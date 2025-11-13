#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from smarthome.mqtt import get_bus, Z2M_BASE

def println(title, payload):
    print(f"\n=== {title} ===")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2))
    else:
        print(payload)


def wait_for_bridge_state(wait_s=0.5):
    bus = get_bus()
    topic = f"{Z2M_BASE}/bridge/state"
    got = {}
    def handler(t, payload): got["p"] = payload
    bus.subscribe_topic(topic, handler)
    # small wait for the retained message to arrive
    import time; t0=time.time()
    while time.time()-t0 < wait_s and "p" not in got:
        time.sleep(0.02)
    return got.get("p", {})


def main():

    state = wait_for_bridge_state(0.5)
    print("bridge/state:", state or "(nothing)")

if __name__ == "__main__":
    main()
