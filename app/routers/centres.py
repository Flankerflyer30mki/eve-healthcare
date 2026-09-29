from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import Centre, CentreTest, DiagnosticTest, User
from app.schemas import CentreCreate, CentreOut, OfferingCreate, OfferingOut

router = APIRouter(prefix="/centres", tags=["centres"])

# Load offerings and their tests in 2 extra queries instead of 1 per centre (avoids N+1)
with_offerings = selectinload(Centre.offerings).selectinload(CentreTest.test)


@router.post("", response_model=CentreOut, status_code=201)
def create_centre(body: CentreCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    centre = Centre(name=body.name, location=body.location)
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@router.get("", response_model=list[CentreOut])
def list_centres(
    location: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Centre).options(with_offerings).order_by(Centre.id).limit(limit).offset(offset)
    if location:
        stmt = stmt.where(Centre.location.ilike(f"%{location}%"))
    return db.scalars(stmt).all()


@router.get("/{centre_id}", response_model=CentreOut)
def get_centre(centre_id: int, db: Session = Depends(get_db)):
    centre = db.scalar(select(Centre).options(with_offerings).where(Centre.id == centre_id))
    if centre is None:
        raise HTTPException(404, "Centre not found")
    return centre


@router.post("/{centre_id}/tests", response_model=OfferingOut, status_code=201)
def add_test_to_centre(
    centre_id: int,
    body: OfferingCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if db.get(Centre, centre_id) is None:
        raise HTTPException(404, "Centre not found")
    if db.get(DiagnosticTest, body.test_id) is None:
        raise HTTPException(404, "Test not found")
    offering = CentreTest(centre_id=centre_id, test_id=body.test_id, price=body.price)
    db.add(offering)
    try:
        db.commit()
    except IntegrityError:  # unique (centre_id, test_id)
        db.rollback()
        raise HTTPException(409, "Centre already offers this test")
    db.refresh(offering)
    return offering