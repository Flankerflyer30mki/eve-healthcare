from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import Booking, BookingStatus, CentreTest, User
from app.schemas import BookingCreate, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])

# Load centre and test together with the booking (avoids one extra query per row)
load_details = joinedload(Booking.centre_test).options(
    joinedload(CentreTest.centre), joinedload(CentreTest.test)
)


def get_own_booking(db: Session, booking_id: int, user: User, lock: bool = False) -> Booking:
    """Fetch a booking only if it belongs to this user. Someone else's booking looks like a missing one."""
    stmt = select(Booking).where(Booking.id == booking_id, Booking.user_id == user.id)
    stmt = stmt.with_for_update() if lock else stmt.options(load_details)
    booking = db.scalar(stmt)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    return booking


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(body: BookingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offering = db.scalar(
        select(CentreTest).where(CentreTest.centre_id == body.centre_id, CentreTest.test_id == body.test_id)
    )
    if offering is None:
        raise HTTPException(404, "This centre does not offer that test")
    booking = Booking(
        user_id=user.id,
        centre_test_id=offering.id,
        appointment_at=body.appointment_at,
        amount=offering.price,  # price snapshot
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=list[BookingOut])
def list_bookings(
    status: BookingStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Booking).options(load_details).where(Booking.user_id == user.id)
    if status:
        stmt = stmt.where(Booking.status == status)
    return db.scalars(stmt.order_by(Booking.id.desc()).limit(limit).offset(offset)).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_own_booking(db, booking_id, user)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = get_own_booking(db, booking_id, user, lock=True)
    if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
        raise HTTPException(409, f"Cannot cancel a {booking.status.value} booking")
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking