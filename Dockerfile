FROM python:3.12

COPY . /usr/src/app

RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt

ENV MQTT_BROKER=
ENV MQTT_PORT=1883
ENV MQTT_USER=
ENV MQTT_PASSWORD=
ENV MASJID_SURL=
ENV POLL_INTERVAL=5
ENV CAST_PROXY_PORT=8000
ENV RELAY_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

EXPOSE 8000

CMD ["python", "/usr/src/app/main.py"]
