# livemasjid

A Docker container that pushes the status of a livemasjid stream to MQTT.

## Usage

```bash
docker run -d --name livemasjid \
  -e MQTT_BROKER="ip of mqtt broker" \
  -e MQTT_PORT=1883 \
  -e MQTT_USER="username" \
  -e MQTT_PASSWORD="password" \
  -e MASJID_SURL="http://livemasjid.com/cambridge" \
  -e POLL_INTERVAL=5 \
  sufyanmotala/livemasjid:latest
```

## Home Assistant Example Usage

This can the be utilized in Home Assistant or similar as a trigger for automations such as when to cast the stream to a device.

1. Run the Docker Container on a device on the same network as your Home Assistant device with the following command:

```bash
docker run -d --name livemasjid \
  -e MQTT_BROKER="ip of mqtt broker" \
  -e MQTT_PORT=1883 \
  -e MQTT_USER="username" \
  -e MQTT_PASSWORD="password" \
  -e MASJID_SURL="http://livemasjid.com/cambridge" \
  -e POLL_INTERVAL=5 \
  sufyanmotala/livemasjid:latest
```

2. Install the `Studio Code Server` add-on on Home Assistant.

3. Follow the following guide to install and setup the `MQTT Broker` Add-on: https://youtu.be/dqTn-Gk4Qeo?si=LuSZHHoVtF8OkdJj
   
4. Using the Studio Code Server Integration, add the following to your `configuration.yaml` file on Home Assistant:

```yaml
mqtt:
  - binary_sensor:
      name: "LiveMasjid Stream Status"
      state_topic: "livemasjid/status"
```

5. Create an automation in Home Assistant to trigger when the `LiveMasjid Stream Status` changes to `ON`:

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

6. Create an automation in Home Assistant to trigger when the `LiveMasjid Stream Status` changes to `OFF`:

```yaml
alias: Stop Masjid Stream When Inactive
description: ""
trigger:
  - platform: state
    entity_id:
      - binary_sensor.livemasjid_stream_status
    from: "on"
    to: "off"
condition: []
action:
  - service: media_player.media_stop
    metadata: {}
    data: {}
    target:
      entity_id: media_player.gaming_room
mode: single
```
