FROM python:3
LABEL authors="sten"

COPY . .

EXPOSE 5000

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "main.py"]