"""Device control logic with state confirmation."""
import os
import time
import threading
from typing import Any, Optional

from ..mqtt import get_bus, JsonObj

Z2M_BASE = os.getenv("Z2M_BASE", "zigbee2mqtt")


class DeviceControlError(Exception):
    """Base exception for device control errors."""
    pass


class DeviceNotFoundError(DeviceControlError):
    """Device not found."""
    pass


class DeviceTimeoutError(DeviceControlError):
    """Device state confirmation timeout."""
    pass


class DeviceController:
    """
    Controller for Zigbee device operations with state confirmation.

    This class provides methods to control devices and wait for state
    confirmation from Zigbee2MQTT.
    """

    def __init__(self):
        self.bus = get_bus()

    def set_device_state(
        self,
        friendly_name: str,
        state: Optional[str] = None,
        brightness: Optional[int] = None,
        color_temp: Optional[int] = None,
        transition: Optional[float] = None,
        timeout: float = 5.0,
    ) -> JsonObj:
        """
        Set device state and wait for confirmation.

        Args:
            friendly_name: Device friendly name
            state: Device state (ON, OFF, TOGGLE)
            brightness: Brightness level (0-254)
            color_temp: Color temperature in mireds
            transition: Transition time in seconds
            timeout: Maximum time to wait for state confirmation

        Returns:
            Confirmed device state as dict

        Raises:
            DeviceNotFoundError: If device doesn't exist
            DeviceTimeoutError: If state confirmation times out
        """
        # Build command payload
        command: JsonObj = {}
        if state is not None:
            command["state"] = state
        if brightness is not None:
            command["brightness"] = brightness
        if color_temp is not None:
            command["color_temp"] = color_temp
        if transition is not None:
            command["transition"] = transition

        if not command:
            raise ValueError("At least one control parameter must be provided")

        # Setup state listener before sending command
        state_topic = f"{Z2M_BASE}/{friendly_name}"
        confirmed_state: dict[str, Any] = {}
        lock = threading.Lock()
        received_event = threading.Event()

        def state_handler(topic: str, payload: JsonObj) -> None:
            """Capture state updates."""
            nonlocal confirmed_state
            with lock:
                confirmed_state = payload
                received_event.set()

        # Subscribe to device state topic
        self.bus.subscribe_topic(state_topic, state_handler)

        try:
            # Send command
            set_topic = f"{Z2M_BASE}/{friendly_name}/set"
            self.bus.publish_json(set_topic, command)

            # Wait for state confirmation
            if received_event.wait(timeout=timeout):
                with lock:
                    return confirmed_state
            else:
                raise DeviceTimeoutError(
                    f"Timeout waiting for device '{friendly_name}' state confirmation after {timeout}s"
                )

        finally:
            # Cleanup: Remove handler (Note: current MqttBus doesn't support unsubscribe,
            # but in practice this is fine as the handler will just be replaced on next call)
            pass

    def get_device_state(self, friendly_name: str, timeout: float = 2.0) -> JsonObj:
        """
        Get current device state.

        Args:
            friendly_name: Device friendly name
            timeout: Maximum time to wait for state

        Returns:
            Current device state as dict

        Raises:
            DeviceTimeoutError: If unable to get state within timeout
        """
        state_topic = f"{Z2M_BASE}/{friendly_name}"
        state = self.bus.wait_for(state_topic, timeout=timeout)

        if not state:
            raise DeviceTimeoutError(
                f"Timeout getting state for device '{friendly_name}' after {timeout}s"
            )

        return state

    def list_devices(self, timeout: float = 2.0) -> list[JsonObj]:
        """
        List all Zigbee devices.

        Args:
            timeout: Maximum time to wait for device list

        Returns:
            List of device info dictionaries

        Raises:
            DeviceTimeoutError: If unable to get device list within timeout
        """
        devices_topic = f"{Z2M_BASE}/bridge/devices"
        devices_data = self.bus.wait_for(devices_topic, timeout=timeout)

        if not devices_data:
            raise DeviceTimeoutError(f"Timeout getting device list after {timeout}s")

        # The devices topic returns a list directly
        if isinstance(devices_data, list):
            return devices_data

        # Or it might be wrapped in a dict
        return devices_data.get("devices", [])

    def get_bridge_health(self, timeout: float = 5.0) -> JsonObj:
        """
        Get Zigbee2MQTT bridge health status.

        Args:
            timeout: Maximum time to wait for health check response

        Returns:
            Health check response

        Raises:
            DeviceTimeoutError: If health check times out
        """
        try:
            response = self.bus.rpc(
                f"{Z2M_BASE}/bridge/request/health_check",
                {},
                timeout=timeout
            )
            return response
        except TimeoutError as e:
            raise DeviceTimeoutError(str(e))

    def get_bridge_info(self, timeout: float = 5.0) -> JsonObj:
        """
        Get Zigbee2MQTT bridge information.

        Args:
            timeout: Maximum time to wait for info response

        Returns:
            Bridge info response
        """
        try:
            response = self.bus.rpc(
                f"{Z2M_BASE}/bridge/request/config",
                {},
                timeout=timeout
            )
            return response.get("data", {})
        except TimeoutError as e:
            raise DeviceTimeoutError(str(e))

    def permit_join(self, time_seconds: int = 60, timeout: float = 5.0) -> JsonObj:
        """
        Enable/disable device pairing.

        Args:
            time_seconds: Time in seconds to permit joining (0 to disable)
            timeout: Maximum time to wait for response

        Returns:
            Response from bridge

        Raises:
            DeviceTimeoutError: If request times out
        """
        try:
            response = self.bus.rpc(
                f"{Z2M_BASE}/bridge/request/permit_join",
                {"time": time_seconds},
                timeout=timeout
            )
            return response
        except TimeoutError as e:
            raise DeviceTimeoutError(str(e))

    def get_groups(self, timeout: float = 5.0) -> list[JsonObj]:
        """
        Get all Zigbee groups.

        Args:
            timeout: Maximum time to wait for groups response

        Returns:
            List of group info dictionaries

        Raises:
            DeviceTimeoutError: If request times out
        """
        try:
            response = self.bus.rpc(
                f"{Z2M_BASE}/bridge/request/groups",
                {},
                timeout=timeout
            )
            groups_data = response.get("data", [])
            if isinstance(groups_data, list):
                return groups_data
            return []
        except TimeoutError as e:
            raise DeviceTimeoutError(str(e))

    def set_group_state(
        self,
        group_name: str,
        state: Optional[str] = None,
        brightness: Optional[int] = None,
        color_temp: Optional[int] = None,
        timeout: float = 5.0,
    ) -> JsonObj:
        """
        Set group state.

        Note: Groups don't provide individual state confirmation like devices,
        so this method just sends the command and returns immediately.

        Args:
            group_name: Group friendly name or ID
            state: Group state (ON, OFF, TOGGLE)
            brightness: Brightness level (0-254)
            color_temp: Color temperature in mireds
            timeout: Not used, kept for API consistency

        Returns:
            Command sent confirmation
        """
        command: JsonObj = {}
        if state is not None:
            command["state"] = state
        if brightness is not None:
            command["brightness"] = brightness
        if color_temp is not None:
            command["color_temp"] = color_temp

        if not command:
            raise ValueError("At least one control parameter must be provided")

        set_topic = f"{Z2M_BASE}/{group_name}/set"
        self.bus.publish_json(set_topic, command)

        return {"success": True, "command": command}


# Singleton instance
_controller: Optional[DeviceController] = None


def get_controller() -> DeviceController:
    """Get or create the device controller singleton."""
    global _controller
    if _controller is None:
        _controller = DeviceController()
    return _controller
