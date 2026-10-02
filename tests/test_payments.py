def pay(client, headers, booking_id, outcome):
    return client.post("/payments/", json={"booking_id": booking_id, "outcome": outcome}, headers=headers)


def test_successful_payment_confirms_booking(client, login, create_booking):
    headers = login()
    booking_id = create_booking(headers)
    response = pay(client, headers, booking_id, "SUCCESS")
    assert response.status_code == 201
    assert response.json()["booking_status"] == "CONFIRMED"


def test_failed_payment_fails_booking(client, login, create_booking):
    headers = login()
    booking_id = create_booking(headers)
    response = pay(client, headers, booking_id, "FAILED")
    assert response.status_code == 201
    assert response.json()["booking_status"] == "FAILED"


def test_cannot_pay_twice(client, login, create_booking, payment_count):
    headers = login()
    booking_id = create_booking(headers)
    pay(client, headers, booking_id, "SUCCESS")
    assert pay(client, headers, booking_id, "SUCCESS").status_code == 409
    assert payment_count() == 1


def test_cannot_pay_cancelled_booking(client, login, create_booking):
    headers = login()
    booking_id = create_booking(headers)
    client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    assert pay(client, headers, booking_id, "SUCCESS").status_code == 409


def test_cannot_pay_for_another_users_booking(client, login, create_booking):
    booking_id = create_booking(login("a@test.com"))
    assert pay(client, login("b@test.com"), booking_id, "SUCCESS").status_code == 404


def test_unknown_booking_is_404(client, login):
    assert pay(client, login(), 999, "SUCCESS").status_code == 404