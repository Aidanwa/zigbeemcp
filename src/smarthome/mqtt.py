from __future__ import annotations
import json, os, threading, time, uuid
from typing import Callable, Dict, Optional
import paho.mqtt.client as mqtt

# ---- Env-configurable defaults ----
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME") or None
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD") or None
Z2M_BASE = os.getenv("Z2M_BASE", "zigbee2mqtt")
CLIENT_ID = os.getenv("MQTT_CLIENT_ID", f"smarthome-bus-{uuid.uuid4().hex[:6]}")

JsonObj = dict
MsgHandler = Callable[[str, JsonObj], None]

def _try_json(data: bytes) -> JsonObj:
    try:
        s = data.decode()
        return json.loads(s) if s else {}
    except Exception:
        return {"_raw": data.decode("utf-8", "ignore")}

class MqttBus:
    """
    Single shared MQTT connection with:
      • background loop_start()
      • publish_json()
      • subscribe_prefix() and subscribe_topic()
      • RPC helper using Zigbee2MQTT bridge request/response with 'transaction'
      • wait_for() helper to fetch one retained/live message on a topic
    """
    def __init__(self) -> None:
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, clean_session=True)
        if MQTT_USERNAME:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self._lock = threading.Lock()
        self._prefix_handlers: Dict[str, MsgHandler] = {}
        self._topic_handlers: Dict[str, MsgHandler] = {}
        self._wait_by_key: Dict[str, tuple[str, JsonObj]] = {}
        self._one_shot: Dict[str, JsonObj] = {}

        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        self.client.loop_start()

    # ---- callbacks ----
    def _on_connect(self, c, u, flags, rc, props=None):
        # Subscribe broadly so dev tools see traffic; specific handlers gate delivery.
        c.subscribe(f"{Z2M_BASE}/#")
        c.subscribe(f"{Z2M_BASE}/bridge/response/#")

    def _on_disconnect(self, c, u, rc, props=None):
        # loop_start handles reconnects
        pass

    def _on_message(self, c, u, msg: mqtt.MQTTMessage):
        topic = msg.topic
        payload = _try_json(msg.payload)

        # exact-topic handlers first
        with self._lock:
            if topic in self._topic_handlers:
                try:
                    self._topic_handlers[topic](topic, payload)
                except Exception:
                    pass

            # prefix fan-out
            for prefix, cb in list(self._prefix_handlers.items()):
                if topic.startswith(prefix):
                    try:
                        cb(topic, payload)
                    except Exception:
                        pass

            # RPC correlation
            if isinstance(payload, dict):
                key = str(payload.get("transaction") or payload.get("id") or "")
                if key:
                    self._wait_by_key[key] = (topic, payload)

            # wait_for one-shot by topic
            if topic in self._one_shot:
                self._one_shot[topic] = payload

    # ---- public API ----
    def publish_json(self, topic: str, obj: Optional[JsonObj] = None, *, qos: int = 0, retain: bool = False) -> None:
        self.client.publish(topic, json.dumps(obj or {}), qos=qos, retain=retain)

    def subscribe_prefix(self, prefix: str, handler: MsgHandler) -> None:
        """
        Subscribe to all topics under `prefix` (adds '/#' if no wildcard present).
        If caller supplies a wildcard ('#' or '+'), use it verbatim.
        """
        with self._lock:
            self._prefix_handlers[prefix] = handler
        if ("#" in prefix) or ("+" in prefix):
            topic_filter = prefix
        else:
            topic_filter = prefix.rstrip("/") + "/#"
        self.client.subscribe(topic_filter)

    def subscribe_topic(self, topic: str, handler: MsgHandler) -> None:
        with self._lock:
            self._topic_handlers[topic] = handler
        self.client.subscribe(topic)

    def rpc(self, request_topic: str, payload: Optional[JsonObj] = None, timeout: float = 5.0) -> JsonObj:
        """
        Publish to zigbee2mqtt/bridge/request/<op> and wait for zigbee2mqtt/bridge/response/<op>
        with matching 'transaction' (preferred) or 'id' (fallback).
        """
        corr = uuid.uuid4().hex[:8]
        body: JsonObj = dict(payload or {})
        body.setdefault("transaction", corr)
        body.setdefault("id", corr)

        self.client.publish(request_topic, json.dumps(body))
        t0 = time.time()
        while time.time() - t0 < timeout:
            with self._lock:
                hit = self._wait_by_key.pop(corr, None)
            if hit:
                topic, pl = hit
                if topic.startswith(f"{Z2M_BASE}/bridge/response/"):
                    return pl
            time.sleep(0.02)
        raise TimeoutError(f"RPC timeout: {request_topic} transaction={corr}")

    def wait_for(self, topic: str, timeout: float = 2.0) -> JsonObj:
        """
        Wait for one message on topic (useful for retained topics like bridge/devices).
        """
        with self._lock:
            self._one_shot[topic] = {}
        self.client.subscribe(topic)
        t0 = time.time()
        while time.time() - t0 < timeout:
            with self._lock:
                pl = self._one_shot.get(topic, {})
                if pl:
                    self._one_shot.pop(topic, None)
                    return pl
            time.sleep(0.02)
        self._one_shot.pop(topic, None)
        return {}

# Singleton for convenience
_bus: Optional[MqttBus] = None
def get_bus() -> MqttBus:
    global _bus
    if _bus is None:
        _bus = MqttBus()
    return _bus
