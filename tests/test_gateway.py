"""Tests for the gateway health check and basic routing."""


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_endpoint_exists(client):
    response = client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "hello"}]
    })
    assert response.status_code == 200
