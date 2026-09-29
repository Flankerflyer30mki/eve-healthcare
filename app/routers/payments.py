import hashlib
import hmac
import random
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Booking, BookingStatus, Payment, PaymentStatus, User, WebhookEvent
from app.routers.bookings import get_own_booking
from app.schemas import PaymentCreate, PaymentOut, WebhookPayload

router = APIRouter(prefix="/payments", tags=["payments"])

SUCCESS_RATE = 0.8


def settle_booking(booking: Booking, result: PaymentStatus) -> None:
    """A booking only moves out of PENDING. Anything else is left untouched."""
    if booking.status == BookingStatus.PENDING:
        booking.status = BookingStatus.CONFIRMED if result == PaymentStatus.SUCCESS else BookingStatus.FAILED


def payment_out(payment: Payment, booking: Booking) -> PaymentOut:
    return PaymentOut(
        id=payment.id,
        booking_id=payment.booking_id,
        amount=payment.amount,
        status=payment.status,
        provider_ref=payment.provider_ref,
        created_at=payment.created_at,
        booking_status=booking.status,
    )


@router.post("/", response_model=PaymentOut, status_code=201)
def create_payment(body: PaymentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = get_own_booking(db, body.booking_id, user, lock=True)
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(409, f"Booking is {booking.status.value}; only PENDING bookings can be paid")

    outcome = body.outcome or (PaymentStatus.SUCCESS if random.random() < SUCCESS_RATE else PaymentStatus.FAILED)
    payment = Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status=outcome,
        provider_ref=f"pay_{uuid.uuid4().hex[:16]}",
    )
    db.add(payment)
    settle_booking(booking, outcome)
    db.commit()
    db.refresh(payment)
    db.refresh(booking)
    return payment_out(payment, booking)


async def verify_signature(request: Request, x_signature: str | None = Header(None)) -> None:
    raw_body = await request.body()
    expected = hmac.new(settings.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not x_signature or not hmac.compare_digest(expected, x_signature):
        raise HTTPException(401, "Invalid signature")


@router.post("/webhook/")
def payment_webhook(
    payload: WebhookPayload,
    _: None = Depends(verify_signature),
    db: Session = Depends(get_db),
):
    # Lock the booking first: everything below runs one-at-a-time per booking
    booking = db.scalar(select(Booking).where(Booking.id == payload.booking_id).with_for_update())
    if booking is None:
        raise HTTPException(404, "Booking not found")

    # Record the event. The unique event_id rejects replays.
    db.add(WebhookEvent(event_id=payload.event_id, payload=payload.model_dump(mode="json")))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"result": "duplicate"}

    # Unique provider_ref: never create a second payment for the same provider payment
    known = db.scalar(select(Payment).where(Payment.provider_ref == payload.provider_ref))
    if known is None:
        db.add(
            Payment(
                booking_id=booking.id,
                amount=booking.amount,
                status=payload.status,
                provider_ref=payload.provider_ref,
            )
        )
        settle_booking(booking, payload.status)
    db.commit()
    return {"result": "ignored" if known else "processed"}