from fastapi.testclient import TestClient


def test_ws_returns_person_overview(client: TestClient) -> None:
    pid = client.post(
        "/persons", json={"name": "Ws", "age": 22, "email": "ws@example.com"}
    ).json()["id"]

    with client.websocket_connect("/ws/persons") as ws:
        ws.send_json({"person_id": pid})
        data = ws.receive_json()

    assert data["id"] == pid
    assert data["name"] == "Ws"
    assert data["is_premium"] is False


def test_ws_unknown_person_reports_not_found(client: TestClient) -> None:
    with client.websocket_connect("/ws/persons") as ws:
        ws.send_json({"person_id": 9999})
        data = ws.receive_json()

    assert data == {"error": "not found"}
