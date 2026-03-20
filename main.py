import os
import sys
from time import sleep
import requests
import paho.mqtt.client as mqtt
import re

required_env_vars = [
    'MQTT_BROKER',
    'MQTT_PORT',
    'MQTT_USER',
    'MQTT_PASSWORD',
    'MASJID_SURL',
    'POLL_INTERVAL'
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
MQTT_TOPIC = 'elivemasjid/status'
MQTT_CLIENT_ID = 'elivemasjid'
STATUS_URL = f"https://emasjidlive.co.uk/listen/{MASJID_SURL}"
RELAY_URL = f"https://relay.emasjidlive.uk/{MASJID_SURL}?"
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL'))
regex_pattern = r"token=(?P<token>[^&]+)&expires=(?P<expires>\d+)"
last_token = ""

class LiveMasjid:

    def __init__(self, masjid_surl):
        self.masjid_surl = masjid_surl
        
    def extract_and_cast(self, rawSource):
        global last_token
        match = re.search(regex_pattern, rawSource )
        if match:
            current_token = match.group('token')
            current_expires = match.group('expires')
            if current_token != last_token:
                last_token = current_token # Update our tracker
                return RELAY_URL + f"token={current_token}&expires={current_expires}"                
            else:
                print("Token hasn't changed. Skipping update.")
                return RELAY_URL + f"token={last_token}&expires={current_expires}"                
        else:
            print("Could not find a valid token in the source string.")
    def get_stream_status(self):
        try:
            print(STATUS_URL)
            response = requests.get(STATUS_URL, timeout=(0.5))
            responseText = response.text
            if "Stream Currently Offline" in responseText or response.status_code != 200:
                if response.status_code != 200:
                    print(response.status_code, "Connection Error")
                return False
            elif response.status_code == 200:
                print("Stream Currently Online")
                return self.extract_and_cast(responseText)
            else:
                print("Unable to determine status")
                return False
        except requests.exceptions.RequestException as e:
            print("HTTP Request failed")
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
        print(f"Publishing status to MQTT Broker: {status if status else 'OFF'}")
        client.publish(MQTT_TOPIC, {"status":"ON","URL":status} if status else "OFF")

    def run(self):
        print("Starting LiveMasjid MQTT Publisher")
        client = self.connect_mqtt()
        client.loop_start()
        # We initialise status with OFF first before checking
        self.publish(client,'OFF')
        while True:
            status = self.get_stream_status()
            self.publish(client, status)
            print(f"Sleeping for {POLL_INTERVAL} seconds\n")
            sleep(POLL_INTERVAL)


if __name__ == '__main__':
    live_masjid = LiveMasjid(MASJID_SURL)
    live_masjid.run()
