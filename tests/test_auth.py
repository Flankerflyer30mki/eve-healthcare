def test_signup_returns_user_without_password(client):
    response = client.post("/auth/signup", json={"email": "a@test.com", "full_name": "A", "password": "password123"})
    assert response.status_code == 201
    assert "password" not in response.text


def test_duplicate_signup_is_409(client):
    body = {"email": "a@test.com", "full_name": "A", "password": "password123"}
    client.post("/auth/signup", json=body)
    assert client.post("/auth/signup", json=body).status_code == 409


def test_signup_validation(client):
    response = client.post("/auth/signup", json={"email": "bad", "full_name": "A", "password": "short"})
    assert response.status_code == 422


def test_login_wrong_password_is_401(client, login):
    login()
    response = client.post("/auth/login", json={"email": "a@test.com", "password": "wrong-password"})
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code in (401, 403)


def test_me_with_token(client, login):
    response = client.get("/auth/me", headers=login())
    assert response.status_code == 200
    assert response.json()["email"] == "a@test.com"