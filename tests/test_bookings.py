def test_booking_is_pending_with_price_snapshot(client, login, offering, appointment):
    response = client.post("/bookings", json={**offering, "appointment_at": appointment}, headers=login())
    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    assert response.json()["amount"] == "300.00"


def test_centre_must_offer_the_test(client, login, offering, appointment):
    body = {"centre_id": offering["centre_id"], "test_id": 999, "appointment_at": appointment}
    assert client.post("/bookings", json=body, headers=login()).status_code == 404


def test_past_appointment_is_rejected(client, login, offering):
    body = {**offering, "appointment_at": "2020-01-01T10:00:00Z"}
    assert client.post("/bookings", json=body, headers=login()).status_code == 422


def test_appointment_without_timezone_is_rejected(client, login, offering):
    body = {**offering, "appointment_at": "2099-01-01T10:00:00"}
    assert client.post("/bookings", json=body, headers=login()).status_code == 422


def test_booking_requires_login(client, offering, appointment):
    response = client.post("/bookings", json={**offering, "appointment_at": appointment})
    assert response.status_code in (401, 403)


def test_unknown_booking_is_404(client, login):
    assert client.get("/bookings/999", headers=login()).status_code == 404


def test_user_cannot_see_or_cancel_another_users_booking(client, login, create_booking):
    booking_id = create_booking(login("a@test.com"))
    other = login("b@test.com")
    assert client.get(f"/bookings/{booking_id}", headers=other).status_code == 404
    assert client.post(f"/bookings/{booking_id}/cancel", headers=other).status_code == 404
    assert client.get("/bookings", headers=other).json() == []


def test_cancel_then_cancel_again(client, login, create_booking):
    headers = login()
    booking_id = create_booking(headers)
    first = client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "CANCELLED"
    assert client.post(f"/bookings/{booking_id}/cancel", headers=headers).status_code == 409