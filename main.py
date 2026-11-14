import os
import sys
import logging
from time import sleep
import requests
import paho.mqtt.client as mqtt
import re
import json
from audio_proxy import AudioProxyServer

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

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
    logger.critical("Missing required environment variables: %s", ", ".join(missing_vars))
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
                logger.info("Found a new relay token; refreshing the proxy stream")
                return RELAY_URL + f"token={current_token}&expires={current_expires}"
            else:
                logger.debug("Relay token is unchanged")
                return RELAY_URL + f"token={last_token}&expires={current_expires}"
        else:
            logger.error("Stream page did not contain a valid relay token")

    def get_stream_status(self):
        try:
            logger.debug("Checking stream status")
            response = requests.get(
                STATUS_URL,
                headers={"User-Agent": RELAY_USER_AGENT},
                timeout=(0.5)
            )
            responseText = response.text
            if "Stream Currently Offline" in responseText or response.status_code != 200:
                if response.status_code != 200:
                    logger.warning("Stream status check returned HTTP %s", response.status_code)
                return False
            elif response.status_code == 200:
                return self.extract_and_cast(responseText)
            else:
                logger.warning("Unable to determine stream status")
                return False
        except requests.exceptions.RequestException as error:
            logger.warning("Stream status request failed (%s)", type(error).__name__)
            return False

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("Connected to MQTT broker")
            else:
                logger.error("MQTT broker connection failed with return code %s", rc)

        client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.on_connect = on_connect
        try:
            client.connect(MQTT_BROKER, MQTT_PORT)
        except Exception:
            logger.exception("Could not connect to MQTT broker at %s:%s", MQTT_BROKER, MQTT_PORT)
            sys.exit(1)

        return client

    def publish(self, client, status):
        state = "ON" if status else "OFF"
        payload = json.dumps({"status": "ON", "url": status}) if status else json.dumps({"status":"OFF"})
        try:
            result = client.publish(MQTT_TOPIC, payload)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error("MQTT publish failed with return code %s", result.rc)
            else:
                logger.debug("Published stream status %s to MQTT topic %s", state, MQTT_TOPIC)
        except Exception:
            logger.exception("Could not publish stream status to MQTT")

    def call_home_assistant(self, service, data):
        try:
            response = requests.post(
                f"{HA_URL}/api/services/media_player/{service}",
                headers={"Authorization": f"Bearer {HA_TOKEN}"},
                json=data,
                timeout=10
            )
            response.raise_for_status()
            logger.info("Home Assistant %s request succeeded for %s", service, HA_MEDIA_PLAYER)
            return True
        except requests.exceptions.HTTPError as error:
            logger.error(
                "Home Assistant %s request failed with HTTP %s",
                service,
                error.response.status_code
            )
            return False
        except requests.exceptions.RequestException as error:
            logger.error("Home Assistant %s request failed (%s)", service, type(error).__name__)
            return False

    def update_cast(self, stream_url):
        self.audio_proxy.set_stream_url(stream_url)
        if stream_url and not self.current_media_url:
            logger.info("Starting playback on %s using the audio proxy", HA_MEDIA_PLAYER)
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
            else:
                logger.error("Could not start playback on %s", HA_MEDIA_PLAYER)
        elif not stream_url and self.current_media_url:
            logger.info("Stopping playback on %s because the stream is offline", HA_MEDIA_PLAYER)
            stopped = self.call_home_assistant(
                "media_stop",
                {"entity_id": HA_MEDIA_PLAYER}
            )
            if stopped:
                self.current_media_url = None
            else:
                logger.error("Could not stop playback on %s", HA_MEDIA_PLAYER)

    def run(self):
        logger.info("Starting LiveMasjid MQTT publisher and Home Assistant casting")
        logger.info("Polling stream status every %s seconds", POLL_INTERVAL)
        logger.info(
            "Casting target: %s; proxy URL: %s",
            HA_MEDIA_PLAYER,
            CAST_PROXY_URL
        )
        self.audio_proxy.start()
        client = self.connect_mqtt()
        client.loop_start()
        self.publish(client, False)
        last_stream_state = None
        try:
            while True:
                status = self.get_stream_status()
                state = "ON" if status else "OFF"
                if state != last_stream_state:
                    logger.info("Stream state changed to %s", state)
                    last_stream_state = state
                self.publish(client, status)
                self.update_cast(status)
                sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")


if __name__ == '__main__':
    live_masjid = LiveMasjid(MASJID_SURL)
    live_masjid.run()
