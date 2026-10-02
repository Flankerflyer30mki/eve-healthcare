def event(booking_id, status="SUCCESS", event_id="evt_1", provider_ref="prov_1"):
    return {"event_id": event_id, "booking_id": booking_id, "provider_ref": provider_ref, "status": status}


def booking_status(client, headers, booking_id):
    return client.get(f"/bookings/{booking_id}", headers=headers).json()["status"]


def test_webhook_confirms_pending_booking(client, login, create_booking, send_webhook):
    headers = login()
    booking_id = create_booking(headers)
    response = send_webhook(event(booking_id))
    assert response.status_code == 200
    assert response.json() == {"result": "processed"}
    assert booking_status(client, headers, booking_id) == "CONFIRMED"


def test_duplicate_event_changes_nothing(client, login, create_booking, send_webhook, payment_count):
    booking_id = create_booking(login())
    send_webhook(event(booking_id))
    response = send_webhook(event(booking_id))
    assert response.json() == {"result": "duplicate"}
    assert payment_count() == 1


def test_same_payment_with_new_event_creates_no_second_payment(login, create_booking, send_webhook, payment_count):
    booking_id = create_booking(login())
    send_webhook(event(booking_id, event_id="evt_1"))
    response = send_webhook(event(booking_id, event_id="evt_2"))
    assert response.json() == {"result": "ignored"}
    assert payment_count() == 1


def test_late_failure_cannot_flip_a_confirmed_booking(client, login, create_booking, send_webhook):
    headers = login()
    booking_id = create_booking(headers)
    send_webhook(event(booking_id, "SUCCESS", "evt_1", "prov_1"))
    send_webhook(event(booking_id, "FAILED", "evt_2", "prov_2"))
    assert booking_status(client, headers, booking_id) == "CONFIRMED"


def test_failed_webhook_fails_pending_booking(client, login, create_booking, send_webhook):
    headers = login()
    booking_id = create_booking(headers)
    send_webhook(event(booking_id, "FAILED"))
    assert booking_status(client, headers, booking_id) == "FAILED"


def test_webhook_cannot_revive_cancelled_booking(client, login, create_booking, send_webhook):
    headers = login()
    booking_id = create_booking(headers)
    client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    send_webhook(event(booking_id, "SUCCESS"))
    assert booking_status(client, headers, booking_id) == "CANCELLED"


def test_bad_signature_is_rejected(client, login, create_booking, send_webhook, payment_count):
    headers = login()
    booking_id = create_booking(headers)
    assert send_webhook(event(booking_id), signature="bad").status_code == 401
    assert booking_status(client, headers, booking_id) == "PENDING"
    assert payment_count() == 0


def test_unknown_booking_is_404(send_webhook):
    assert send_webhook(event(999)).status_code == 404


def test_invalid_status_is_422(login, create_booking, send_webhook):
    booking_id = create_booking(login())
    assert send_webhook(event(booking_id, status="PAID")).status_code == 422