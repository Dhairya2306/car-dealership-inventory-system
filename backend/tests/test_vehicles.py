from decimal import Decimal

import pytest

VEHICLE = {
    "make": "Toyota",
    "model": "Corolla",
    "category": "Sedan",
    "price": "24500.25",
    "quantity": 2,
}


@pytest.fixture
def auth_headers(client):
    credentials = {"email": "inventory@example.com", "password": "Inventory test password!"}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    token = client.post("/api/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_vehicle(client, auth_headers, **overrides):
    response = client.post("/api/vehicles", headers=auth_headers, json=VEHICLE | overrides)
    assert response.status_code == 201, response.text
    return response.json()


def test_vehicle_create_as_normal_user(client, auth_headers):
    vehicle = add_vehicle(client, auth_headers, make=" Toyota ")
    assert vehicle["make"] == "Toyota"
    assert vehicle["quantity"] == 2
    assert Decimal(vehicle["price"]) == Decimal("24500.25")
    assert {
        "id",
        "make",
        "model",
        "category",
        "price",
        "quantity",
        "created_at",
        "updated_at",
    } == set(vehicle)


def test_vehicle_listing_is_paginated(client, auth_headers):
    created = [add_vehicle(client, auth_headers, model=model) for model in ["Corolla", "Camry"]]
    first = client.get("/api/vehicles?limit=1&offset=0", headers=auth_headers)
    second = client.get("/api/vehicles?limit=1&offset=1", headers=auth_headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["total"] == second.json()["total"] == 2
    assert first.json()["limit"] == 1 and second.json()["offset"] == 1
    assert {first.json()["items"][0]["id"], second.json()["items"][0]["id"]} == {
        v["id"] for v in created
    }


@pytest.mark.parametrize("method", ["get", "post"])
def test_vehicle_create_and_list_require_login(client, method):
    response = client.request(
        method, "/api/vehicles", **({"json": VEHICLE} if method == "post" else {})
    )
    assert response.status_code == 401
