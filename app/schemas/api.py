from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RoleName = Literal["ADMIN", "REGISTERED_USER"]
UserStatus = Literal["ACTIVE", "SUSPENDED"]
RoomStatus = Literal["AVAILABLE", "OCCUPIED", "MAINTENANCE", "OUT_OF_SERVICE"]
BookingStatus = Literal["PENDING", "CONFIRMED", "CHECKED_IN", "CHECKED_OUT", "CANCELLED"]
PaymentMethod = Literal["CARD", "CASH", "BANK_TRANSFER"]


def _email(value: str) -> str:
    cleaned = value.strip().lower()
    if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
        raise ValueError("Enter a valid email address.")
    return cleaned


def _strong_password(value: str) -> str:
    if len(value) < 10:
        raise ValueError("Use at least 10 characters.")
    if not any(character.islower() for character in value):
        raise ValueError("Include at least one lowercase letter.")
    if not any(character.isupper() for character in value):
        raise ValueError("Include at least one uppercase letter.")
    if not any(character.isdigit() for character in value):
        raise ValueError("Include at least one number.")
    return value


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginRequest(RequestModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class RegisterRequest(RequestModel):
    full_name: str = Field(min_length=2, max_length=80)
    email: str
    phone: str | None = Field(default=None, max_length=24)
    password: str

    _normalise_email = field_validator("email")(_email)
    _validate_password = field_validator("password")(_strong_password)


class RefreshRequest(RequestModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(RequestModel):
    refresh_token: str | None = None


class ProfileUpdateRequest(RequestModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str | None = Field(default=None, max_length=24)


class ChangePasswordRequest(RequestModel):
    current_password: str = Field(min_length=1)
    new_password: str

    _validate_password = field_validator("new_password")(_strong_password)


class UserCreateRequest(RegisterRequest):
    role: RoleName = "REGISTERED_USER"


class UserUpdateRequest(RequestModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str | None = Field(default=None, max_length=24)
    role: RoleName
    status: UserStatus


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str | None
    role: RoleName
    status: UserStatus
    created_at: datetime


class AuthSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class BiometricEnrollRequest(RequestModel):
    device_id: str = Field(min_length=8, max_length=64)
    device_label: str = Field(default="", max_length=80)


class BiometricLoginRequest(RequestModel):
    email: str
    device_id: str = Field(min_length=8, max_length=64)
    biometric_token: str = Field(min_length=16, max_length=255)

    _normalise_email = field_validator("email")(_email)


class BiometricDeviceResponse(BaseModel):
    id: int
    device_id: str
    device_label: str
    created_at: datetime
    last_used_at: datetime | None


class BiometricEnrollResponse(BiometricDeviceResponse):
    # Returned exactly once, at enrolment. The server only keeps its hash.
    biometric_token: str


class RoomTypeWriteRequest(RequestModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=600)
    max_occupancy: int = Field(ge=1, le=20)
    base_rate: float = Field(gt=0, le=10000)
    amenities: list[str] = Field(default_factory=list)
    image_url: str = ""


class RoomTypeResponse(BaseModel):
    id: int
    name: str
    description: str
    max_occupancy: int
    base_rate: float
    amenities: list[str]
    image_url: str


class RoomWriteRequest(RequestModel):
    room_number: str = Field(min_length=1, max_length=10)
    floor: int = Field(ge=0, le=50)
    status: RoomStatus
    room_type_id: int = Field(ge=1)
    nightly_rate: float = Field(gt=0, le=10000)
    description: str = Field(default="", max_length=600)


class RoomResponse(BaseModel):
    id: int
    room_number: str
    floor: int
    status: RoomStatus
    room_type_id: int
    room_type: RoomTypeResponse
    nightly_rate: float
    description: str


class AvailabilityResponse(BaseModel):
    room: RoomResponse
    nights: int
    nightly_rate: float
    subtotal: float
    taxes: float
    total: float
    currency: str


class BookingCreateRequest(RequestModel):
    room_id: int = Field(ge=1)
    check_in: date
    check_out: date
    guests: int = Field(ge=1, le=8)
    special_requests: str | None = Field(default=None, max_length=500)


class BookingUpdateRequest(RequestModel):
    check_in: date | None = None
    check_out: date | None = None
    guests: int | None = Field(default=None, ge=1, le=8)
    status: BookingStatus | None = None
    special_requests: str | None = Field(default=None, max_length=500)


class BookingResponse(BaseModel):
    id: int
    reference: str
    user_id: int
    guest_name: str
    guest_email: str
    room_id: int
    room: RoomResponse
    check_in: date
    check_out: date
    guests: int
    nights: int
    nightly_rate: float
    subtotal: float
    taxes: float
    total_price: float
    currency: str
    status: BookingStatus
    special_requests: str | None
    created_at: datetime
    updated_at: datetime


class PaymentCreateRequest(RequestModel):
    booking_id: int = Field(ge=1)
    amount: float = Field(gt=0)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    method: PaymentMethod


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: float
    currency: str
    method: PaymentMethod
    paid_at: datetime


class OccupancyResponse(BaseModel):
    occupied: int
    available: int
    maintenance: int
    total_rooms: int
    occupancy_rate: float


class MonthRevenueResponse(BaseModel):
    month: str
    revenue: float


class RevenueResponse(BaseModel):
    currency: str
    monthly_revenue: float
    previous_month_revenue: float
    average_daily_rate: float
    by_month: list[MonthRevenueResponse]


class DashboardResponse(BaseModel):
    occupancy: OccupancyResponse
    revenue: RevenueResponse
    total_users: int
    active_bookings: int
    arrivals_today: int
    departures_today: int
    recent_bookings: list[BookingResponse]


class GuestWriteRequest(RequestModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=24)
    email: str
    address: str | None = Field(default=None, max_length=200)

    _normalise_email = field_validator("email")(_email)


class GuestResponse(GuestWriteRequest):
    id: int


class MessageResponse(BaseModel):
    message: str

