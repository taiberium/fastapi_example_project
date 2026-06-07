from fastapi.testclient import TestClient


def test_save_person_returns_created_person(client: TestClient) -> None:
    response = client.post(
        "/persons",
        json={"name": "Alice", "age": 30, "email": "alice@example.com"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["name"] == "Alice"
    assert body["age"] == 30
    assert body["email"] == "alice@example.com"


def test_save_person_rejects_negative_age(client: TestClient) -> None:
    response = client.post(
        "/persons",
        json={"name": "Bob", "age": -1, "email": "bob@example.com"},
    )

    assert response.status_code == 422


def test_find_returns_only_persons_younger_than_age(client: TestClient) -> None:
    client.post("/persons", json={"name": "Young", "age": 20, "email": "young@example.com"})
    client.post("/persons", json={"name": "Old", "age": 40, "email": "old@example.com"})

    response = client.get("/persons", params={"age": 30})

    assert response.status_code == 200
    names = [person["name"] for person in response.json()]
    assert names == ["Young"]


def test_find_rejects_negative_age_query(client: TestClient) -> None:
    response = client.get("/persons", params={"age": -5})

    assert response.status_code == 422


def test_find_by_email_returns_person(client: TestClient) -> None:
    client.post(
        "/persons",
        json={"name": "Eve", "age": 28, "email": "eve@example.com"},
    )

    response = client.get("/persons/by-email", params={"email": "eve@example.com"})

    assert response.status_code == 200
    assert response.json()["name"] == "Eve"


def test_find_by_email_returns_404_when_absent(client: TestClient) -> None:
    response = client.get("/persons/by-email", params={"email": "nobody@example.com"})

    assert response.status_code == 404
