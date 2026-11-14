# livemasjid

A Docker container that casts a livemasjid stream through Home Assistant and publishes its status to MQTT.

## Usage

```bash
docker run -d --name livemasjid \
  -e MQTT_BROKER="ip of mqtt broker" \
  -e MQTT_PORT=1883 \
  -e MQTT_USER="username" \
  -e MQTT_PASSWORD="password" \
  -e MASJID_SURL="http://livemasjid.com/cambridge" \
  -e HA_URL="http://homeassistant.local:8123" \
  -e HA_TOKEN="your_home_assistant_long_lived_access_token" \
  -e HA_MEDIA_PLAYER="media_player.google_home" \
  -e CAST_PROXY_URL="http://192.168.1.20:8000/stream" \
  -e RELAY_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  -p 8000:8000 \
  -e POLL_INTERVAL=5 \
  sufyanmotala/livemasjid:latest
```

Replace `192.168.1.20` with the Docker host's LAN IP. The proxy fetches the relay
audio with the configured `RELAY_USER_AGENT` and streams it to Home Assistant's
media player, so Google Home only needs access to the proxy URL. If emasjid
requires a specific User-Agent value, set that exact value here. The container
also continues to publish stream status over MQTT and asks Home Assistant to
stop playback when the stream goes offline. Create a long-lived access token in
your Home Assistant profile and use the exact entity ID for your Google Home.
No Home Assistant play/stop automation is needed for casting.

## Home Assistant Example Usage

The MQTT status can optionally be used for monitoring or other automations.

1. Add the https://github.com/alexbelgium/hassio-addons repository to Home Assistant and install the `Portainer` add-on. Follow the `Portainer` guide to ensure it is running.

2. Follow the following guide to install and setup the `MQTT Broker` add-on: https://youtu.be/dqTn-Gk4Qeo?si=LuSZHHoVtF8OkdJj

3. Using the Portainer add-on (default username is admin and default password is homeassistant), create a new container by first clicking Live connect and then Containers. Click Add container and use the `sufyanmotala/livemasjid:latest` image. Add the following environment variables:

```
MQTT_BROKER: ip of mqtt broker # Replace with your MQTT broker IP, usually the IP of your Home Assistant instance
MQTT_PORT: 1883
MQTT_USER: username # Replace with your MQTT username
MQTT_PASSWORD: password # Replace with your MQTT password
MASJID_SURL: http://livemasjid.com/cambridge # Replace with your masjids stream URL
HA_URL: http://homeassistant.local:8123
HA_TOKEN: your_home_assistant_long_lived_access_token
HA_MEDIA_PLAYER: media_player.google_home # Replace with your Google Home entity ID
CAST_PROXY_URL: http://192.168.1.20:8000/stream # Docker host LAN IP; publish container port 8000
RELAY_USER_AGENT: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36
POLL_INTERVAL: 5
```

In Portainer, also publish container port `8000` to host port `8000`. `CAST_PROXY_URL`
must use the host address and port reachable by Home Assistant and the Google Home,
not the container's internal address.

The container now starts and stops casting automatically through Home Assistant.
If you only need direct casting, skip the play/stop automations below. The MQTT
status sensor remains optional and can still be used for monitoring.

4. Install the `Studio Code Server` add-on on Home Assistant if you want to configure the optional MQTT status sensor.

5. Using the `Studio Code Server` Integration, add the following to your `configuration.yaml` file on Home Assistant:

```yaml
mqtt:
  - binary_sensor:
      name: "LiveMasjid Stream Status"
      state_topic: "elivemasjid/status"
      value_template: "{{ value_json.status }}"
```

6. Only use these automations instead of direct casting; enabling them alongside direct casting may start playback twice. Create an automation in Home Assistant to trigger when the `LiveMasjid Stream Status` changes to `ON`:

```yaml
alias: Cast Masjid Stream When Active
description: ""
trigger:
  - platform: state
    entity_id:
      - binary_sensor.livemasjid_stream_status
    from: "OFF"
    to: "ON"
condition: []
action:
  - service: media_player.play_media
    target:
      entity_id: media_player.gaming_room
    data:
      media_content_id: http://livemasjid.com:8000/activestream.mp3 # Replace with your masjids stream URL
      media_content_type: music
    metadata: {}
mode: single
```

7. Create an automation in Home Assistant to trigger when the `LiveMasjid Stream Status` changes to `OFF`:

```yaml
alias: Stop Masjid Stream When Inactive
description: ""
trigger:
  - platform: state
    entity_id:
      - binary_sensor.livemasjid_stream_status
    from: "ON"
    to: "OFF"
condition: []
action:
  - service: media_player.media_stop
    metadata: {}
    data: {}
    target:
      entity_id: media_player.gaming_room
mode: single
```
