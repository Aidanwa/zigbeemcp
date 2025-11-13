#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys, time
from typing import Any, Dict, List, Optional

from smarthome.mqtt import get_bus, Z2M_BASE

def println(title: str, payload: Any):
    print(f"\n=== {title} ===")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2))
    else:
        print(payload)

def wait_for_exact(topic: str, *, wait_s: float = 1.0) -> dict:
    """Wait once for a specific topic (retained or live)."""
    bus = get_bus()
    return bus.wait_for(topic, timeout=wait_s) or {}

def require_bridge_online(timeout: float = 2.0) -> dict:
    topic = f"{Z2M_BASE}/bridge/state"
    pl = wait_for_exact(topic, wait_s=timeout)
    if not isinstance(pl, dict) or pl.get("state") != "online":
        raise SystemExit(f"[FAIL] {topic} not 'online' within {timeout}s; got: {pl!r}")
    println("Bridge state", pl)
    return pl

def rpc_health_check(timeout: float = 5.0) -> dict:
    bus = get_bus()
    resp = bus.rpc(f"{Z2M_BASE}/bridge/request/health_check", {}, timeout=timeout)
    if resp.get("status") != "ok" or not resp.get("data", {}).get("healthy", False):
        raise SystemExit(f"[FAIL] health_check RPC bad response: {resp!r}")
    println("Health check (RPC)", resp)
    return resp

def read_devices(timeout: float = 2.0) -> List[dict]:
    topic = f"{Z2M_BASE}/bridge/devices"
    pl = wait_for_exact(topic, wait_s=timeout)
    if not isinstance(pl, list) or len(pl) == 0:
        raise SystemExit(f"[FAIL] no devices from {topic} within {timeout}s; got: {type(pl).__name__}")
    # Coordinator should always be present
    if not any(d.get("type") == "Coordinator" for d in pl if isinstance(d, dict)):
        print("[WARN] coordinator not found in devices payload")
    println("Devices (retained)", {"count": len(pl), "sample": pl[:2]})
    return pl

def find_device_names(devices: List[dict]) -> List[str]:
    names = []
    for d in devices:
        n = d.get("friendly_name")
        if isinstance(n, str):
            names.append(n)
    return names

def toggle_light_once(friendly: str, wait_feedback_s: float = 2.0) -> dict:
    """
    Sends TOGGLE to zigbee2mqtt/<friendly>/set and waits for any state payload on the device topic.
    Returns the payload we saw (if any).
    """
    bus = get_bus()
    dev_topic = f"{Z2M_BASE}/{friendly}"
    set_topic = f"{dev_topic}/set"

    got: Dict[str, dict] = {}

    def handler(topic: str, payload: dict):
        # Capture first state-bearing message
        if topic == dev_topic and isinstance(payload, dict):
            got.setdefault("p", payload)

    bus.subscribe_topic(dev_topic, handler)
    bus.publish_json(set_topic, {"state": "TOGGLE"})

    t0 = time.time()
    while time.time() - t0 < wait_feedback_s and "p" not in got:
        time.sleep(0.02)

    return got.get("p", {})

def test_toggle(friendly: str, *, round_trips: int = 1, wait_feedback_s: float = 2.0) -> List[dict]:
    """
    Toggle a light N times; collect observed payloads.
    """
    println(f"Toggle test → {friendly}", f"{round_trips} toggle(s)")
    out: List[dict] = []
    for i in range(round_trips):
        p = toggle_light_once(friendly, wait_feedback_s=wait_feedback_s)
        out.append(p or {"_note": "no feedback"})
        print(f"  • toggle {i+1}:", p if p else "(no feedback)")
        # small spacing between toggles
        if i + 1 < round_trips:
            time.sleep(0.3)
    return out

def rpc_permit_join(seconds: int, timeout: float = 5.0) -> dict:
    bus = get_bus()
    payload = {"time": int(seconds)}
    resp = bus.rpc(f"{Z2M_BASE}/bridge/request/permit_join", payload, timeout=timeout)
    if resp.get("status") != "ok":
        raise SystemExit(f"[FAIL] permit_join RPC failed: {resp!r}")
    println("Permit join (RPC)", resp)
    return resp

def rpc_networkmap(timeout: float = 30.0) -> dict:
    """
    Requests a network map. Can be slow and can cause short sluggishness on the network.
    """
    bus = get_bus()
    resp = bus.rpc(f"{Z2M_BASE}/bridge/request/networkmap", {}, timeout=timeout)
    # Responses vary; just print a head and status.
    println("Network map (RPC)", {"status": resp.get("status"), "keys": list(resp.keys())})
    return resp

def main():
    ap = argparse.ArgumentParser(description="Comprehensive Zigbee2MQTT smoke test")
    ap.add_argument("--timeout", type=float, default=5.0, help="default RPC timeout seconds")
    ap.add_argument("--state-timeout", type=float, default=1.0, help="bridge/state wait seconds")
    ap.add_argument("--devices-timeout", type=float, default=2.0, help="bridge/devices wait seconds")
    ap.add_argument("--permit-join", type=int, default=None, help="issue permit_join for N seconds (0 disables)")
    ap.add_argument("--networkmap", action="store_true", help="request networkmap (can be slow)")
    ap.add_argument("--light", action="append", help="friendly name of a light to toggle (can repeat)")
    ap.add_argument("--round-trips", type=int, default=1, help="how many toggles per light")
    ap.add_argument("--wait-feedback", type=float, default=2.0, help="wait seconds for device feedback after toggle")
    ap.add_argument("--summary-only", action="store_true", help="suppress payload dumps; print concise OK/FAIL")
    args = ap.parse_args()

    # Show environment context
    from smarthome.mqtt import MQTT_HOST, MQTT_PORT
    print("Context:",
          f"MQTT={MQTT_HOST}:{MQTT_PORT}",
          f"Z2M_BASE={Z2M_BASE}",
          f"timeouts: rpc={args.timeout}s state={args.state-timeout if hasattr(args,'state-timeout') else args.state_timeout}s devices={args.devices_timeout}s",
          sep=" | ")

    failures = 0
    report = []

    # Step 0: bridge/state online
    try:
        st = require_bridge_online(timeout=args.state_timeout)
        report.append(("bridge/state", "ok", st))
    except SystemExit as e:
        failures += 1
        report.append(("bridge/state", "fail", str(e)))
        print(e, file=sys.stderr)

    # Step 1: health_check RPC
    try:
        hc = rpc_health_check(timeout=args.timeout)
        report.append(("health_check", "ok", hc))
    except SystemExit as e:
        failures += 1
        report.append(("health_check", "fail", str(e)))
        print(e, file=sys.stderr)

    # Step 2: devices snapshot
    try:
        devs = read_devices(timeout=args.devices_timeout)
        names = find_device_names(devs)
        report.append(("devices", "ok", {"count": len(devs), "names_sample": names[:5]}))
        if not args.summary_only:
            println("Device names (first 10)", names[:10])
    except SystemExit as e:
        failures += 1
        report.append(("devices", "fail", str(e)))
        print(e, file=sys.stderr)
        devs, names = [], []

    # Step 3: optional permit_join
    if args.permit_join is not None:
        try:
            pj = rpc_permit_join(args.permit_join, timeout=args.timeout)
            report.append(("permit_join", "ok", pj))
        except SystemExit as e:
            failures += 1
            report.append(("permit_join", "fail", str(e)))
            print(e, file=sys.stderr)

    # Step 4: optional networkmap
    if args.networkmap:
        try:
            nm = rpc_networkmap(timeout=max(args.timeout, 30.0))
            report.append(("networkmap", "ok", {"status": nm.get("status")}))
        except SystemExit as e:
            failures += 1
            report.append(("networkmap", "fail", str(e)))
            print(e, file=sys.stderr)

    # Step 5: optional toggle(s)
    if args.light:
        for friendly in args.light:
            try:
                obs = test_toggle(friendly, round_trips=max(1, args.round_trips), wait_feedback_s=args.wait_feedback)
                report.append((f"toggle:{friendly}", "ok", {"observations": obs}))
            except Exception as e:
                failures += 1
                report.append((f"toggle:{friendly}", "fail", repr(e)))
                print(f"[FAIL] toggle {friendly}: {e}", file=sys.stderr)

    # Summary
    print("\n===== SUMMARY =====")
    for name, status, data in report:
        if args.summary_only:
            print(f"{name}: {status}")
        else:
            try:
                print(f"{name}: {status}")
                if isinstance(data, (dict, list)):
                    print(json.dumps(data, indent=2))
                else:
                    print(str(data))
            except Exception:
                print(f"{name}: {status} (unprintable data)")

    if failures:
        print(f"\n{failures} check(s) failed.", file=sys.stderr)
        sys.exit(2)
    print("\nAll checks passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
