import requests
import pandas as pd
import json
import time
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

    def request(self):
        self.r = requests.get("https://api.dawum.de/")
        self.data = json.loads(self.r.text)
    #print(data)
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

    def plot_party(self, party_id):
        party_name = self.party_name_by_id(party_id)
        party_data = ([], [])

        for i in range(0, len(self.survey_list()), 50):
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
        df = pd.DataFrame({'Date': pd.to_datetime(d), 'Result': r})
        df.set_index('Date', inplace=True)
        return df

    def get_color_for_party(self, party_id):
        return self.party_colors[str(party_id)]


    def render_plot(self):
        party_ids = ["5", "1", "2", "3", "4", "7", "23"]
        dataframes = [self.plot_party(pid) for pid in party_ids]

        all_data = pd.concat(dataframes, axis=1, join='outer')
        all_data.columns = party_ids

        smoothed_data = all_data.rolling(window=8, min_periods=1).mean()

        plt.figure(figsize=(12, 6))
        for party_id in party_ids:
            plt.plot(smoothed_data.index, smoothed_data[party_id], antialiased=True, color=self.get_color_for_party(party_id) ,linewidth=2, label=f'{self.party_name_by_id(party_id)}')

        plt.legend()
        plt.title("approximation of election results")
        plt.xlabel("Date")
        plt.ylabel("Result")
        plt.xticks(rotation=45)
        plt.tight_layout()
        filename = f"static/{time.strftime("%Y%m%d-%H%M%S", time.localtime())}.png"
        if os.path.exists(self.previous_picture):
            os.remove(self.previous_picture)
        self.previous_picture = filename
        plt.savefig(filename)
        return filename



bw = BundestagsWatch()
@application.route("/")
def root():
    bw.request()
    name = bw.render_plot()
    return f"<center><img src='{name}'></center>"

if __name__ == "__main__":
    application.run(host = "0.0.0.0")
