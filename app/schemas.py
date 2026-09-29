from datetime import datetime, timezone
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import BookingStatus
from app.models import BookingStatus, PaymentStatus


# ---------- auth ----------
class SignupRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- centres and tests ----------
class CentreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)


class TestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class OfferingCreate(BaseModel):
    test_id: int
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class OfferingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: Decimal
    test: TestOut


class CentreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    offerings: list[OfferingOut] = []


class CentreBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str


# ---------- bookings ----------
class BookingCreate(BaseModel):
    centre_id: int
    test_id: int
    appointment_at: AwareDatetime  # rejects datetimes without a timezone

    @field_validator("appointment_at")
    @classmethod
    def must_be_future(cls, value):
        if value <= datetime.now(timezone.utc):
            raise ValueError("appointment_at must be in the future")
        return value


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: BookingStatus
    amount: Decimal
    appointment_at: datetime
    created_at: datetime
    centre: CentreBrief
    test: TestOut

# ---------- payments ----------
class PaymentCreate(BaseModel):
    booking_id: int
    outcome: PaymentStatus | None = None  # optional: force the simulated result (useful for tests)


class PaymentOut(BaseModel):
    id: int
    booking_id: int
    amount: Decimal
    status: PaymentStatus
    provider_ref: str
    created_at: datetime
    booking_status: BookingStatus


class WebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=64)
    booking_id: int
    provider_ref: str = Field(min_length=1, max_length=64)
    status: PaymentStatus