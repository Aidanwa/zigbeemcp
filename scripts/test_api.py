#!/usr/bin/env python3
"""
Test script for the Smart Home API.

This script exercises all the API endpoints to verify functionality.
Run this on your Raspberry Pi after starting the API server.

Usage:
    uv run scripts/test_api.py --help
    uv run scripts/test_api.py --base-url http://localhost:8000 --api-key YOUR_KEY
    uv run scripts/test_api.py --device AidanBedroom1 --toggle
"""
import argparse
import json
import sys
from typing import Any, Optional

try:
    import requests
except ImportError:
    print("Error: requests library not installed")
    print("Install with: pip install requests")
    sys.exit(1)


class APITester:
    """Test client for the Smart Home API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"
        kwargs["headers"] = self.headers
        response = requests.request(method, url, **kwargs)
        return response

    def print_response(self, response: requests.Response, title: str):
        """Pretty print API response."""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
        print(f"Status: {response.status_code} {response.reason}")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
        except Exception:
            print(response.text)

    # === System Endpoints ===

    def test_health(self):
        """Test health check endpoint."""
        response = self._request("GET", "/health")
        self.print_response(response, "Health Check")
        return response.status_code == 200

    def test_root(self):
        """Test root endpoint."""
        response = self._request("GET", "/")
        self.print_response(response, "Root Endpoint")
        return response.status_code == 200

    # === Device Endpoints ===

    def test_list_devices(self):
        """Test listing all devices."""
        response = self._request("GET", "/api/devices")
        self.print_response(response, "List All Devices")
        return response.status_code == 200

    def test_get_device_state(self, device_name: str):
        """Test getting device state."""
        response = self._request("GET", f"/api/devices/{device_name}")
        self.print_response(response, f"Get Device State: {device_name}")
        return response.status_code == 200

    def test_set_device_state(
        self,
        device_name: str,
        state: Optional[str] = None,
        brightness: Optional[int] = None,
        color_temp: Optional[int] = None,
    ):
        """Test setting device state."""
        payload = {}
        if state:
            payload["state"] = state
        if brightness is not None:
            payload["brightness"] = brightness
        if color_temp is not None:
            payload["color_temp"] = color_temp

        response = self._request(
            "POST",
            f"/api/devices/{device_name}/set",
            json=payload
        )
        self.print_response(response, f"Set Device State: {device_name}")
        return response.status_code == 200

    # === Group Endpoints ===

    def test_list_groups(self):
        """Test listing all groups."""
        response = self._request("GET", "/api/groups")
        self.print_response(response, "List All Groups")
        return response.status_code == 200

    def test_set_group_state(
        self,
        group_name: str,
        state: Optional[str] = None,
        brightness: Optional[int] = None,
    ):
        """Test setting group state."""
        payload = {}
        if state:
            payload["state"] = state
        if brightness is not None:
            payload["brightness"] = brightness

        response = self._request(
            "POST",
            f"/api/groups/{group_name}/set",
            json=payload
        )
        self.print_response(response, f"Set Group State: {group_name}")
        return response.status_code == 200

    # === Bridge Endpoints ===

    def test_bridge_health(self):
        """Test bridge health check."""
        response = self._request("GET", "/api/bridge/health")
        self.print_response(response, "Bridge Health Check")
        return response.status_code == 200

    def test_bridge_info(self):
        """Test getting bridge info."""
        response = self._request("GET", "/api/bridge/info")
        self.print_response(response, "Bridge Information")
        return response.status_code == 200

    def test_permit_join(self, time_seconds: int = 0):
        """Test permit join."""
        response = self._request(
            "POST",
            "/api/bridge/permit_join",
            json={"time": time_seconds}
        )
        self.print_response(response, f"Permit Join ({time_seconds}s)")
        return response.status_code == 200

    # === Event Endpoints ===

    def test_get_events(self, device: Optional[str] = None, limit: int = 10):
        """Test getting event history."""
        params = {"limit": limit}
        if device:
            params["device"] = device

        response = self._request("GET", "/api/events", params=params)
        self.print_response(response, f"Event History (limit={limit})")
        return response.status_code == 200

    # === Combined Tests ===

    def run_full_test_suite(self, test_device: Optional[str] = None):
        """Run all tests."""
        results = {}

        print("\n" + "="*60)
        print("SMART HOME API - FULL TEST SUITE")
        print("="*60)

        # System tests
        results["health"] = self.test_health()
        results["root"] = self.test_root()

        # Bridge tests
        results["bridge_health"] = self.test_bridge_health()
        results["bridge_info"] = self.test_bridge_info()

        # Device tests
        results["list_devices"] = self.test_list_devices()

        if test_device:
            results["get_device_state"] = self.test_get_device_state(test_device)
            results["toggle_device"] = self.test_set_device_state(
                test_device, state="TOGGLE"
            )

        # Group tests
        results["list_groups"] = self.test_list_groups()

        # Event tests
        results["get_events"] = self.test_get_events(device=test_device, limit=5)

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status} - {test_name}")

        total = len(results)
        passed = sum(results.values())
        print(f"\nPassed: {passed}/{total}")

        return all(results.values())


def main():
    parser = argparse.ArgumentParser(
        description="Test the Smart Home API endpoints"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="API key for authentication"
    )
    parser.add_argument(
        "--device",
        help="Device friendly name to test with (e.g., AidanBedroom1)"
    )
    parser.add_argument(
        "--toggle",
        action="store_true",
        help="Toggle the specified device state"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full test suite"
    )

    args = parser.parse_args()

    tester = APITester(args.base_url, args.api_key)

    try:
        if args.full:
            success = tester.run_full_test_suite(test_device=args.device)
            sys.exit(0 if success else 1)
        elif args.toggle and args.device:
            tester.test_set_device_state(args.device, state="TOGGLE")
        elif args.device:
            tester.test_get_device_state(args.device)
        else:
            # Default: show API info and list devices
            tester.test_health()
            tester.test_bridge_health()
            tester.test_list_devices()

    except requests.exceptions.ConnectionError:
        print(f"\n✗ ERROR: Could not connect to {args.base_url}")
        print("Make sure the API server is running.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
