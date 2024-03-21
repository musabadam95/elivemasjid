FROM python:3.12

COPY . /usr/src/app

RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt

ENV MQTT_BROKER=
ENV MQTT_PORT=1883
ENV MQTT_USER=
ENV MQTT_PASSWORD=
ENV MASJID_SURL=
ENV POLL_INTERVAL=5

CMD ["python", "/usr/src/app/main.py", "--mqtt-broker", "$MQTT_BROKER", "--mqtt-port", "$MQTT_PORT", "--mqtt-user", "$MQTT_USER", "--mqtt-password", "$MQTT_PASSWORD", "--masjid-surl", "$MASJID_SURL"]
