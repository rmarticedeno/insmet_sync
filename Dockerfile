FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY crontab /etc/cron/crontab

RUN crontab /etc/cron/crontab

COPY . .

ENTRYPOINT printenv > /etc/environment && crond && python cron.py && python main.py