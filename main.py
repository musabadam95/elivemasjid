import os
import sys
from time import sleep
import requests
import paho.mqtt.client as mqtt

required_env_vars = [
    'MQTT_BROKER',
    'MQTT_PORT',
    'MQTT_USER',
    'MQTT_PASSWORD',
    'MASJID_SURL'
]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

MQTT_BROKER = os.getenv('MQTT_BROKER')
MQTT_PORT = int(os.getenv('MQTT_PORT'))
MQTT_USER = os.getenv('MQTT_USER')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
MASJID_SURL = os.getenv('MASJID_SURL')

MQTT_TOPIC = 'livemasjid/status'
MQTT_CLIENT_ID = 'livemasjid'

STATUS_URL = 'https://www.livemasjid.com/api/get_mountdetail_new.php'
STREAM_STATUS_GREEN = 'green'

POLL_INTERVAL = int(os.getenv('POLL_INTERVAL'))


class LiveMasjid:

    def __init__(self, masjid_surl):
        self.masjid_surl = masjid_surl

    def get_stream_status(self):
        try:
            response = requests.get(STATUS_URL)
            if response.status_code != 200:
                return False

            status = response.json()
            mounts = status.get('mounts', [])
            for mount in mounts:
                if mount.get('surl') == self.masjid_surl:
                    return mount.get("sstatus", "red") == STREAM_STATUS_GREEN
            return False
        except requests.exceptions.RequestException as e:
            print(f"HTTP Request failed: {e}")
            return False

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            print("Connected to MQTT Broker!" if rc == 0 else f"Failed to connect, return code {rc}\n")

        client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.on_connect = on_connect

        try:
            client.connect(MQTT_BROKER, MQTT_PORT)
        except Exception as e:
            print(f"MQTT Connection failed: {e}")
            sys.exit(1)

        return client

    def publish(self, client, status):
        client.publish(MQTT_TOPIC, "ON" if status else "OFF")

    def run(self):
        client = self.connect_mqtt()
        client.loop_start()
        while True:
            status = self.get_stream_status()
            print(f"Stream status: {'ON' if status else 'OFF'}")
            self.publish(client, status)
            print(f"Published status to MQTT Broker")
            print(f"Sleeping for {POLL_INTERVAL} seconds\n")
            sleep(POLL_INTERVAL)


if __name__ == '__main__':
    live_masjid = LiveMasjid(MASJID_SURL)
    live_masjid.run()
