FROM python:3.13-alpine

WORKDIR /app

COPY install_driver.sh .

RUN chmod +x install_driver.sh && ./install_driver.sh

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x cron.py

ENTRYPOINT python cron.py false && python main.py