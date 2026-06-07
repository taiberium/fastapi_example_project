from fastapi.testclient import TestClient


def test_app_boots_and_serves_health(client: TestClient) -> None:
    # The client fixture builds the app via create_app() and runs startup,
    # so a 200 here proves the application boots and serves requests.
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_exposes_openapi_schema(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200
