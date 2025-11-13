from __future__ import annotations
import json, datetime as dt, signal, sys, time
from smarthome.db import connect
from smarthome.mqtt import get_bus, Z2M_BASE

STATE_PREFIX = f"{Z2M_BASE}/"

def _friendly_from(topic: str) -> str | None:
    # zigbee2mqtt/<friendly>
    parts = topic.split("/")
    return parts[1] if len(parts) == 2 else None

def _handle_device_state(topic: str, data: dict):
    # Only log top-level device state: zigbee2mqtt/<friendly>
    if topic.startswith(Z2M_BASE + "/") and topic.count("/") == 1:
        dev = _friendly_from(topic)
        state = data.get("state")
        if isinstance(state, str):
            state = state.upper()
        brightness = data.get("brightness")
        color_temp = data.get("color_temp")

        with connect() as cn:
            cn.execute(
                """CREATE TABLE IF NOT EXISTS lightevents(
                       id INTEGER PRIMARY KEY,
                       ts TEXT NOT NULL,
                       device TEXT NOT NULL,
                       source TEXT NOT NULL,
                       state TEXT,
                       brightness INTEGER,
                       color_temp INTEGER,
                       payload TEXT NOT NULL
                   )"""
            )
            cn.execute(
                """INSERT INTO lightevents(ts,device,source,state,brightness,color_temp,payload)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    dev or "",
                    "zigbee2mqtt",
                    state,
                    brightness,
                    color_temp,
                    json.dumps(data, separators=(",", ":")),
                ),
            )
        print("logged:", dev, state, brightness, color_temp)

def main():
    bus = get_bus()
    bus.subscribe_prefix(STATE_PREFIX, _handle_device_state)

    def _stop(sig, frm):
        print("logger: shutting down")
        sys.exit(0)

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, _stop)

    print("logger: running (listening on zigbee2mqtt/*)")
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()
