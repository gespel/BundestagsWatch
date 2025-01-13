FROM python:3
LABEL authors="sten"

COPY . .

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "main.py"]