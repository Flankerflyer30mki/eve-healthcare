def test_list_centres_is_public(client, offering):
    response = client.get("/centres")
    assert response.status_code == 200
    assert response.json()[0]["offerings"][0]["price"] == "300.00"


def test_unknown_centre_is_404(client):
    assert client.get("/centres/999").status_code == 404


def test_create_centre_requires_login(client):
    assert client.post("/centres", json={"name": "X", "location": "Y"}).status_code in (401, 403)


def test_cannot_add_same_test_to_centre_twice(client, login, offering):
    response = client.post(
        f"/centres/{offering['centre_id']}/tests",
        json={"test_id": offering["test_id"], "price": "100"},
        headers=login(),
    )
    assert response.status_code == 409