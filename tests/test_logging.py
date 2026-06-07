import logging

from fastapi.testclient import TestClient


def test_create_person_emits_log(client: TestClient, caplog) -> None:
    with caplog.at_level(logging.INFO):
        client.post(
            "/persons",
            json={"name": "Logged", "age": 22, "email": "logged@example.com"},
        )

    messages = " ".join(record.message.lower() for record in caplog.records)
    assert "person" in messages


def test_find_emits_log(client: TestClient, caplog) -> None:
    with caplog.at_level(logging.INFO):
        client.get("/persons", params={"age": 30})

    messages = " ".join(record.message.lower() for record in caplog.records)
    assert "person" in messages
