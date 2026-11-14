import os
import sys
from time import sleep
import requests
import paho.mqtt.client as mqtt
import re
import json
from audio_proxy import AudioProxyServer

required_env_vars = [
    'MQTT_BROKER',
    'MQTT_PORT',
    'MQTT_USER',
    'MQTT_PASSWORD',
    'MASJID_SURL',
    'POLL_INTERVAL',
    'HA_URL',
    'HA_TOKEN',
    'HA_MEDIA_PLAYER',
    'CAST_PROXY_URL'
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
HA_URL = os.getenv('HA_URL').rstrip('/')
HA_TOKEN = os.getenv('HA_TOKEN')
HA_MEDIA_PLAYER = os.getenv('HA_MEDIA_PLAYER')
CAST_PROXY_URL = os.getenv('CAST_PROXY_URL')
CAST_PROXY_PORT = int(os.getenv('CAST_PROXY_PORT', '8000'))
RELAY_USER_AGENT = os.getenv(
    'RELAY_USER_AGENT',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
)
regex_pattern = r"token=(?P<token>[^&]+)&expires=(?P<expires>\d+)"
last_token = ""

class LiveMasjid:

    def __init__(self, masjid_surl):
        self.masjid_surl = masjid_surl
        self.current_media_url = None
        self.audio_proxy = AudioProxyServer(CAST_PROXY_PORT, RELAY_USER_AGENT)
        
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
            response = requests.get(
                STATUS_URL,
                headers={"User-Agent": RELAY_USER_AGENT},
                timeout=(0.5)
            )
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
            print(client.connect(MQTT_BROKER, MQTT_PORT))
        except Exception as e:
            print(f"MQTT Connection failed: {e}")
            sys.exit(1)

        return client

    def publish(self, client, status):
        print(f"Publishing status to MQTT Broker: {status if status else 'OFF'}")
        payload = json.dumps({"status": "ON", "url": status}) if status else json.dumps({"status":"OFF"})
        client.publish(MQTT_TOPIC, payload)

    def call_home_assistant(self, service, data):
        try:
            response = requests.post(
                f"{HA_URL}/api/services/media_player/{service}",
                headers={"Authorization": f"Bearer {HA_TOKEN}"},
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Home Assistant {service} request failed: {e}")
            return False

    def update_cast(self, stream_url):
        self.audio_proxy.set_stream_url(stream_url)
        if stream_url and not self.current_media_url:
            started = self.call_home_assistant(
                "play_media",
                {
                    "entity_id": HA_MEDIA_PLAYER,
                    "media_content_id": CAST_PROXY_URL,
                    "media_content_type": "music"
                }
            )
            if started:
                self.current_media_url = CAST_PROXY_URL
                print(f"Started casting to {HA_MEDIA_PLAYER}")
        elif not stream_url and self.current_media_url:
            stopped = self.call_home_assistant(
                "media_stop",
                {"entity_id": HA_MEDIA_PLAYER}
            )
            if stopped:
                self.current_media_url = None
                print(f"Stopped casting to {HA_MEDIA_PLAYER}")

    def run(self):
        print("Starting LiveMasjid MQTT Publisher and Home Assistant casting")
        self.audio_proxy.start()
        client = self.connect_mqtt()
        client.loop_start()
        self.publish(client, False)
        while True:
            status = self.get_stream_status()
            self.publish(client, status)
            self.update_cast(status)
            print(f"Sleeping for {POLL_INTERVAL} seconds\n")
            sleep(POLL_INTERVAL)


if __name__ == '__main__':
    live_masjid = LiveMasjid(MASJID_SURL)
    live_masjid.run()
