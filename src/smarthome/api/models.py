"""Pydantic models for API request/response validation."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# Request Models

class DeviceSetRequest(BaseModel):
    """Request to set device state."""
    state: Optional[Literal["ON", "OFF", "TOGGLE"]] = Field(
        None,
        description="Device power state"
    )
    brightness: Optional[int] = Field(
        None,
        ge=0,
        le=254,
        description="Brightness level (0-254)"
    )
    color_temp: Optional[int] = Field(
        None,
        ge=153,
        le=500,
        description="Color temperature in mireds (153-500)"
    )
    transition: Optional[float] = Field(
        None,
        ge=0,
        description="Transition time in seconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "state": "ON",
                "brightness": 254,
                "color_temp": 370
            }
        }


class GroupSetRequest(BaseModel):
    """Request to set group state."""
    state: Optional[Literal["ON", "OFF", "TOGGLE"]] = Field(
        None,
        description="Group power state"
    )
    brightness: Optional[int] = Field(
        None,
        ge=0,
        le=254,
        description="Brightness level (0-254)"
    )
    color_temp: Optional[int] = Field(
        None,
        ge=153,
        le=500,
        description="Color temperature in mireds (153-500)"
    )


class PermitJoinRequest(BaseModel):
    """Request to enable/disable device pairing."""
    time: int = Field(
        60,
        ge=0,
        le=254,
        description="Time in seconds to permit joining (0 to disable)"
    )


# Response Models

class DeviceStateResponse(BaseModel):
    """Response containing device state."""
    friendly_name: str
    state: Optional[str] = None
    brightness: Optional[int] = None
    color_temp: Optional[int] = None
    linkquality: Optional[int] = None
    last_seen: Optional[str] = None
    # Allow additional fields from Zigbee2MQTT
    model_config = {"extra": "allow"}


class DeviceInfo(BaseModel):
    """Device information from Zigbee2MQTT."""
    friendly_name: str
    ieee_address: str
    type: str
    supported: bool
    manufacturer: Optional[str] = None
    model_id: Optional[str] = None
    power_source: Optional[str] = None
    definition: Optional[dict[str, Any]] = None
    # Allow additional fields
    model_config = {"extra": "allow"}


class DeviceListResponse(BaseModel):
    """Response containing list of devices."""
    count: int
    devices: list[DeviceInfo]


class GroupInfo(BaseModel):
    """Zigbee group information."""
    id: int
    friendly_name: str
    members: list[dict[str, Any]]
    # Allow additional fields
    model_config = {"extra": "allow"}


class GroupListResponse(BaseModel):
    """Response containing list of groups."""
    count: int
    groups: list[GroupInfo]


class BridgeHealthResponse(BaseModel):
    """Bridge health check response."""
    healthy: bool
    status: str
    transaction: Optional[str] = None


class BridgeInfoResponse(BaseModel):
    """Bridge information response."""
    version: Optional[str] = None
    coordinator: Optional[dict[str, Any]] = None
    network: Optional[dict[str, Any]] = None
    log_level: Optional[str] = None
    permit_join: Optional[bool] = None
    # Allow additional fields
    model_config = {"extra": "allow"}


class EventRecord(BaseModel):
    """Event history record from database."""
    id: int
    ts: str
    device: str
    source: str
    state: Optional[str] = None
    brightness: Optional[int] = None
    color_temp: Optional[int] = None
    payload: str


class EventHistoryResponse(BaseModel):
    """Response containing event history."""
    count: int
    events: list[EventRecord]


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool
    message: str
    data: Optional[dict[str, Any]] = None
