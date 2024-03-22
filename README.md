# livemasjid

A docker container that pushes the status of a livemasjid stream to MQTT.

## Usage

```bash
docker run -d --name livemasjid \
  -e MQTT_BROKER="ip" \
  -e MQTT_PORT=1883 \
  -e MQTT_USER="username" \
  -e MQTT_PASSWORD="password" \
  -e MASJID_SURL="http://livemasjid.com/cambridge" \
  -e POLL_INTERVAL=5 \
  sufyanmotala/livemasjid:latest
```

This can the be utilized in Home Assistant or similar as a trigger for automations such as when to cast the stream to a device.
