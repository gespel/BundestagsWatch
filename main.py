import pprint
import traceback
import gc  # Garbage collector für explizite Speicherbereinigung
from datetime import datetime
from threading import Thread

import requests
import pandas as pd
import json
import time
import matplotlib
matplotlib.use('Agg')  # Backend ohne GUI für bessere Performance in Docker
import matplotlib.pyplot as plt
import os
from flask import Flask

application = Flask(__name__)


class BundestagsWatch:
    def __init__(self):
        self.data = None
        self.r = None
        self.previous_picture = ""
        self.party_colors = {
            "1": "black",
            "2": "red",
            "3": "yellow",
            "4": "green",
            "5": "purple",
            "7": "blue",
            "23": "magenta",
        }
        self.latest_render_time = ""

    def request(self):
        # Alte Daten freigeben vor neuem Request
        if hasattr(self, 'data'):
            del self.data
        if hasattr(self, 'r'):
            del self.r
            
        self.r = requests.get("https://api.dawum.de/", timeout=30)
        self.data = json.loads(self.r.text)
        
        # Response object nach Verwendung freigeben
        self.r.close()
    def num_of_parties(self):
        return len(self.data["Parties"])


    def party_name_by_id(self, party_id):
        parties = self.data["Parties"]
        return parties[str(party_id)]["Shortcut"]


    def survey_by_id(self, party_id):
        surveys = self.data["Surveys"]
        return surveys[str(party_id)]


    def survey_list(self):
        out = []
        for s in self.data["Surveys"]:
            out.append(self.data["Surveys"][s])
        return out


    def parties_in_survey(self, survey):
        out = []
        for party_id in survey["Results"]:
            out.append(party_id)
        return out


    def result_of_party_in_survey(self, survey, party_id):
        return survey["Results"][str(party_id)]

    def plot_party(self, party_id, step):
        party_name = self.party_name_by_id(party_id)
        party_data = ([], [])

        for i in range(0, len(self.survey_list()), step):
            s = self.survey_list()[i]
            if s["Parliament_ID"] == "0":
                for p in self.parties_in_survey(s):
                    if p == party_id:
                        party_data[0].append(s["Date"])
                        party_data[1].append(self.result_of_party_in_survey(s, p))

        # Daten umkehren, damit sie chronologisch sortiert sind
        d = party_data[0]
        r = party_data[1]
        d.reverse()
        r.reverse()

        # DataFrame erstellen
        df = pd.DataFrame({'Date': pd.to_datetime(d), party_id: r})
        df.set_index('Date', inplace=True)
        return df

    def get_color_for_party(self, party_id):
        return self.party_colors[str(party_id)]


    def render_plot(self):
        party_ids = ["5", "1", "2", "3", "4", "7", "23"]
        dataframes = [self.plot_party(pid, 1) for pid in party_ids]
        #dataframes = [df.reset_index(drop=True) for df in dataframes]
        dataframes = [df[~df.index.duplicated()] for df in dataframes]
        all_data = pd.concat(dataframes, axis=1, join='outer')
        smoothed_data = all_data.rolling(window=20, min_periods=1).mean()
        #print(smoothed_data)
        
        # Schließe vorherige plots um Memory Leaks zu vermeiden
        plt.close('all')
        
        fig, ax = plt.subplots(figsize=(12, 6))
        for party_id in party_ids:
            ax.plot(smoothed_data.index, smoothed_data[party_id], antialiased=True, color=self.get_color_for_party(party_id), linewidth=2, label=f'{self.party_name_by_id(party_id)}')

        ax.set_yticks(range(0, int(smoothed_data.max().max()) + 5, 5))
        ax.grid(axis='y', linestyle=':', linewidth=1, alpha=1)
        ax.legend()
        ax.set_title("approximation of election results")
        ax.set_xlabel("Date")
        ax.set_ylabel("Result")
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        filename = "static/current_graph.png"
        if os.path.exists(self.previous_picture):
            os.remove(self.previous_picture)
        self.previous_picture = filename
        
        plt.savefig(filename)  # Ursprüngliche Qualität beibehalten
        plt.close(fig)  # Explizit schließen um Memory zu freigeben
        
        # Memory cleanup
        del dataframes
        del all_data
        del smoothed_data
        
        self.latest_render_time = f"{datetime.now()}"
        if os.path.exists("static/latest_render_time.json"):
            os.remove("static/latest_render_time.json")
        with open("static/latest_render_time.json", "w") as f:  # 'w' statt 'a' um Datei zu überschreiben
            out = {
                "time": self.latest_render_time,
            }
            f.write(json.dumps(out))
        return filename

def renderer():
    bw = BundestagsWatch()
    while True:
        try:
            bw.request()
            bw.render_plot()
            
            # Explizite Garbage Collection nach jedem Zyklus
            gc.collect()
            
            time.sleep(600)
        except Exception as e:
            print("Typ:", type(e))
            print("Nachricht:", e)
            traceback.print_exc()
            time.sleep(60)  # Kurze Pause bei Fehlern um CPU-Last zu reduzieren

@application.route("/")
def root():
    latest_render_time = ""
    with open("static/latest_render_time.json") as f:
        latest_render_time = json.load(f)["time"]

    return f"<title>BundestagsWatch</title><center><img src='static/current_graph.png'><br>Latest render: {latest_render_time}</center>"

if __name__ == "__main__":
    if not os.path.exists("static"):
        os.mkdir("static")
    thread1 = Thread(target=renderer, args=())
    thread1.start()
    application.run(host = "0.0.0.0")
