import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Force a throwaway DB before the app is imported, so tests can never touch real data
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "7486a4f4b9c1619093be818fad45ffccc60303f58c7cba892aaf25bb8b415283"
os.environ["WEBHOOK_SECRET"] = "c80cdd5716246467f81a537a76b514be4f3c384ac8c8e33c028db88de739a7a2"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import Centre, CentreTest, DiagnosticTest, Payment


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    """Returns a function that signs a user up, logs them in, and gives back auth headers."""

    def _login(email="a@test.com"):
        client.post("/auth/signup", json={"email": email, "full_name": "Test", "password": "password123"})
        response = client.post("/auth/login", json={"email": email, "password": "password123"})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
def offering(session_factory):
    with session_factory() as db:
        centre = Centre(name="EVE Noida", location="Noida")
        test = DiagnosticTest(name="CBC")
        db.add(CentreTest(centre=centre, test=test, price=Decimal("300.00")))
        db.commit()
        return {"centre_id": centre.id, "test_id": test.id}


@pytest.fixture
def appointment():
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


@pytest.fixture
def create_booking(client, offering, appointment):
    def _create(headers):
        response = client.post("/bookings", json={**offering, "appointment_at": appointment}, headers=headers)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    return _create


@pytest.fixture
def send_webhook(client):
    """Sends a correctly signed webhook. Pass `signature=` to override it."""

    def _send(payload, signature=None):
        body = json.dumps(payload).encode()
        if signature is None:
            signature = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return client.post(
            "/payments/webhook/",
            content=body,
            headers={"X-Signature": signature, "Content-Type": "application/json"},
        )

    return _send


@pytest.fixture
def payment_count(session_factory):
    def _count():
        with session_factory() as db:
            return db.scalar(select(func.count()).select_from(Payment))

    return _count