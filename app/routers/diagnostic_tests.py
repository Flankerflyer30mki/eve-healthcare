from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import DiagnosticTest, User
from app.schemas import TestCreate, TestOut

router = APIRouter(prefix="/tests", tags=["tests"])


@router.post("", response_model=TestOut, status_code=201)
def create_test(body: TestCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    test = DiagnosticTest(name=body.name)
    db.add(test)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Test already exists")
    db.refresh(test)
    return test


@router.get("", response_model=list[TestOut])
def list_tests(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return db.scalars(select(DiagnosticTest).order_by(DiagnosticTest.id).limit(limit).offset(offset)).all()