"""FastAPI routes for smart home device control."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import verify_api_key
from .device_controller import (
    get_controller,
    DeviceController,
    DeviceTimeoutError,
    DeviceNotFoundError,
)
from .models import (
    DeviceSetRequest,
    DeviceStateResponse,
    DeviceListResponse,
    DeviceInfo,
    GroupSetRequest,
    GroupListResponse,
    GroupInfo,
    BridgeHealthResponse,
    BridgeInfoResponse,
    PermitJoinRequest,
    EventHistoryResponse,
    EventRecord,
    ErrorResponse,
    SuccessResponse,
)
from ..db import connect as db_connect

# Create router
router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])


# === Device Endpoints ===

@router.get(
    "/devices",
    response_model=DeviceListResponse,
    summary="List all devices",
    description="Get a list of all Zigbee devices connected to the bridge",
)
async def list_devices(
    controller: DeviceController = Depends(get_controller),
):
    """List all Zigbee devices."""
    try:
        devices = controller.list_devices()
        return DeviceListResponse(
            count=len(devices),
            devices=[DeviceInfo(**d) for d in devices]
        )
    except DeviceTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list devices: {str(e)}"
        )


@router.get(
    "/devices/{friendly_name}",
    response_model=DeviceStateResponse,
    summary="Get device state",
    description="Get the current state of a specific device",
)
async def get_device_state(
    friendly_name: str,
    controller: DeviceController = Depends(get_controller),
):
    """Get current state of a specific device."""
    try:
        state = controller.get_device_state(friendly_name)
        return DeviceStateResponse(friendly_name=friendly_name, **state)
    except DeviceTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{friendly_name}' not found or not responding"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device state: {str(e)}"
        )


@router.post(
    "/devices/{friendly_name}/set",
    response_model=DeviceStateResponse,
    summary="Control device",
    description="Send a command to control a device (state, brightness, color temperature)",
)
async def set_device_state(
    friendly_name: str,
    request: DeviceSetRequest,
    controller: DeviceController = Depends(get_controller),
):
    """Control a device and wait for state confirmation."""
    try:
        confirmed_state = controller.set_device_state(
            friendly_name=friendly_name,
            state=request.state,
            brightness=request.brightness,
            color_temp=request.color_temp,
            transition=request.transition,
        )
        return DeviceStateResponse(friendly_name=friendly_name, **confirmed_state)
    except DeviceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{friendly_name}' not found"
        )
    except DeviceTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control device: {str(e)}"
        )


# === Group Endpoints ===

@router.get(
    "/groups",
    response_model=GroupListResponse,
    summary="List all groups",
    description="Get a list of all Zigbee groups",
)
async def list_groups(
    controller: DeviceController = Depends(get_controller),
):
    """List all Zigbee groups."""
    try:
        groups = controller.get_groups()
        return GroupListResponse(
            count=len(groups),
            groups=[GroupInfo(**g) for g in groups]
        )
    except DeviceTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list groups: {str(e)}"
        )


@router.post(
    "/groups/{group_name}/set",
    response_model=SuccessResponse,
    summary="Control group",
    description="Send a command to control a group of devices",
)
async def set_group_state(
    group_name: str,
    request: GroupSetRequest,
    controller: DeviceController = Depends(get_controller),
):
    """Control a group of devices."""
    try:
        result = controller.set_group_state(
            group_name=group_name,
            state=request.state,
            brightness=request.brightness,
            color_temp=request.color_temp,
        )
        return SuccessResponse(
            success=True,
            message=f"Group '{group_name}' command sent",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control group: {str(e)}"
        )


# === Bridge Endpoints ===

@router.get(
    "/bridge/health",
    response_model=BridgeHealthResponse,
    summary="Bridge health check",
    description="Check if the Zigbee2MQTT bridge is healthy",
)
async def get_bridge_health(
    controller: DeviceController = Depends(get_controller),
):
    """Get bridge health status."""
    try:
        health = controller.get_bridge_health()
        return BridgeHealthResponse(
            healthy=health.get("data", {}).get("healthy", False),
            status=health.get("status", "unknown"),
            transaction=health.get("transaction")
        )
    except DeviceTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check bridge health: {str(e)}"
        )


@router.get(
    "/bridge/info",
    response_model=BridgeInfoResponse,
    summary="Bridge information",
    description="Get detailed information about the Zigbee2MQTT bridge",
)
async def get_bridge_info(
    controller: DeviceController = Depends(get_controller),
):
    """Get bridge information."""
    try:
        info = controller.get_bridge_info()
        return BridgeInfoResponse(**info)
    except DeviceTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bridge info: {str(e)}"
        )


@router.post(
    "/bridge/permit_join",
    response_model=SuccessResponse,
    summary="Enable device pairing",
    description="Allow new devices to join the Zigbee network for a specified time",
)
async def permit_join(
    request: PermitJoinRequest,
    controller: DeviceController = Depends(get_controller),
):
    """Enable/disable device pairing."""
    try:
        result = controller.permit_join(request.time)
        return SuccessResponse(
            success=True,
            message=f"Permit join {'enabled' if request.time > 0 else 'disabled'}",
            data=result
        )
    except DeviceTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set permit join: {str(e)}"
        )


# === Event History Endpoints ===

@router.get(
    "/events",
    response_model=EventHistoryResponse,
    summary="Query event history",
    description="Get historical device events from the database",
)
async def get_events(
    device: Optional[str] = Query(None, description="Filter by device friendly name"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
):
    """Query event history from the database."""
    try:
        conn = db_connect()
        cursor = conn.cursor()

        # Build query
        query = "SELECT id, ts, device, source, state, brightness, color_temp, payload FROM lightevents"
        conditions = []
        params = []

        if device:
            conditions.append("device = ?")
            params.append(device)
        if start_time:
            conditions.append("ts >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("ts <= ?")
            params.append(end_time)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        events = [
            EventRecord(
                id=row[0],
                ts=row[1],
                device=row[2],
                source=row[3],
                state=row[4],
                brightness=row[5],
                color_temp=row[6],
                payload=row[7],
            )
            for row in rows
        ]

        return EventHistoryResponse(count=len(events), events=events)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query events: {str(e)}"
        )
    finally:
        conn.close()
