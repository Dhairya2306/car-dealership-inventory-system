from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import Role, User, Vehicle

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


@pytest.fixture
def admin_headers(auth_headers, session):
    user = session.scalar(select(User).where(User.email == "inventory@example.com"))
    user.role = Role.ADMIN
    session.commit()
    return auth_headers


def test_vehicle_search_combines_filters_and_inclusive_price_bounds(client, auth_headers):
    wanted = add_vehicle(client, auth_headers)
    add_vehicle(client, auth_headers, make="Honda")
    add_vehicle(client, auth_headers, model="Camry")
    add_vehicle(client, auth_headers, category="SUV")
    add_vehicle(client, auth_headers, price="24500.26")
    response = client.get(
        "/api/vehicles/search",
        headers=auth_headers,
        params={
            "make": " toYo ",
            "model": "ROLL",
            "category": "sedan",
            "min_price": "24500.25",
            "max_price": "24500.25",
            "limit": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == wanted["id"]


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"make": "hOn"}, 1),
        ({"model": "vic"}, 1),
        ({"category": "suv"}, 1),
        ({"min_price": "30000"}, 1),
        ({"max_price": "24500.25"}, 1),
        ({"make": "not present"}, 0),
        ({"category": "sed"}, 0),
        ({"make": "%"}, 0),
        ({"model": "_"}, 0),
    ],
)
def test_vehicle_search_filters_individually_and_escapes_wildcards(
    client, auth_headers, params, expected
):
    add_vehicle(client, auth_headers)
    add_vehicle(client, auth_headers, make="Honda", model="Civic", category="SUV", price="30000")
    response = client.get("/api/vehicles/search", headers=auth_headers, params=params)
    assert response.status_code == 200
    assert response.json()["total"] == expected


def test_vehicle_empty_pages_and_search_pagination(client, auth_headers):
    assert client.get("/api/vehicles", headers=auth_headers).json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }
    add_vehicle(client, auth_headers)
    response = client.get("/api/vehicles/search?make=toy&offset=1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"] == [] and response.json()["total"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"price": "0"},
        {"price": "-1"},
        {"price": "1.001"},
        {"price": "10000000000"},
        {"price": "NaN"},
        {"price": "Infinity"},
        {"price": True},
        {"quantity": -1},
        {"quantity": 1.5},
        {"quantity": True},
        {"quantity": "1"},
        {"quantity": 2147483648},
        {"make": "  "},
        {"model": ""},
        {"category": "\t"},
        {"make": "x" * 101},
        {"id": str(uuid4())},
    ],
)
def test_vehicle_invalid_creation_is_rejected(client, auth_headers, changes):
    response = client.post("/api/vehicles", headers=auth_headers, json=VEHICLE | changes)
    assert response.status_code == 422
    assert client.get("/api/vehicles", headers=auth_headers).json()["total"] == 0


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"offset": "bad"},
        {"offset": 2147483648},
        {"min_price": "-1"},
        {"max_price": "-1"},
        {"min_price": "2", "max_price": "1"},
        {"min_price": "NaN"},
        {"max_price": "Infinity"},
        {"make": " "},
    ],
)
def test_vehicle_invalid_search_is_rejected(client, auth_headers, params):
    assert (
        client.get("/api/vehicles/search", headers=auth_headers, params=params).status_code == 422
    )


def test_vehicle_update_details_preserves_stock_and_id(client, auth_headers):
    vehicle = add_vehicle(client, auth_headers)
    details = {key: value for key, value in VEHICLE.items() if key != "quantity"}
    response = client.put(
        f"/api/vehicles/{vehicle['id']}",
        headers=auth_headers,
        json=details | {"make": " Honda ", "price": "30000.01"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == vehicle["id"]
    assert updated["make"] == "Honda" and updated["price"] == "30000.01"
    assert updated["quantity"] == vehicle["quantity"]
    assert updated["created_at"] == vehicle["created_at"]


@pytest.mark.parametrize("changes", [{"price": "0"}, {"quantity": 99}, {"category": " "}])
def test_vehicle_update_rejects_invalid_details_and_direct_stock_edits(
    client, auth_headers, changes
):
    vehicle = add_vehicle(client, auth_headers)
    details = {key: value for key, value in VEHICLE.items() if key != "quantity"}
    response = client.put(
        f"/api/vehicles/{vehicle['id']}", headers=auth_headers, json=details | changes
    )
    assert response.status_code == 422
    unchanged = client.get("/api/vehicles", headers=auth_headers).json()["items"][0]
    assert unchanged == vehicle


def test_vehicle_admin_can_delete(client, admin_headers):
    vehicle = add_vehicle(client, admin_headers)
    response = client.delete(f"/api/vehicles/{vehicle['id']}", headers=admin_headers)
    assert response.status_code == 204 and response.content == b""
    assert client.get("/api/vehicles", headers=admin_headers).json()["total"] == 0


@pytest.mark.parametrize("operation", ["delete", "restock"])
def test_vehicle_normal_user_cannot_delete_or_restock(client, auth_headers, operation):
    vehicle = add_vehicle(client, auth_headers)
    if operation == "delete":
        response = client.delete(f"/api/vehicles/{vehicle['id']}", headers=auth_headers)
    else:
        response = client.post(
            f"/api/vehicles/{vehicle['id']}/restock", headers=auth_headers, json={"quantity": 1}
        )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", "/search", None),
        ("put", "/{id}", {k: v for k, v in VEHICLE.items() if k != "quantity"}),
        ("delete", "/{id}", None),
        ("post", "/{id}/purchase", None),
        ("post", "/{id}/restock", {"quantity": 1}),
    ],
)
def test_vehicle_other_routes_require_auth(client, method, path, payload):
    response = client.request(
        method, "/api/vehicles" + path.format(id=uuid4()), **({"json": payload} if payload else {})
    )
    assert response.status_code == 401


@pytest.mark.parametrize("operation", ["update", "delete", "purchase", "restock"])
def test_vehicle_missing_returns_404(client, admin_headers, operation):
    path = f"/api/vehicles/{uuid4()}"
    if operation == "update":
        response = client.put(
            path, headers=admin_headers, json={k: v for k, v in VEHICLE.items() if k != "quantity"}
        )
    elif operation == "delete":
        response = client.delete(path, headers=admin_headers)
    else:
        response = client.post(
            path + "/" + operation,
            headers=admin_headers,
            **({"json": {"quantity": 1}} if operation == "restock" else {}),
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Vehicle not found"


def test_vehicle_purchase_one_then_reject_repeated_purchase(client, auth_headers):
    vehicle = add_vehicle(client, auth_headers, quantity=1)
    path = f"/api/vehicles/{vehicle['id']}/purchase"
    purchased = client.post(path, headers=auth_headers)
    assert purchased.status_code == 200 and purchased.json()["quantity"] == 0
    assert client.post(path, headers=auth_headers).status_code == 409
    assert client.get("/api/vehicles", headers=auth_headers).json()["items"][0]["quantity"] == 0


def test_vehicle_zero_stock_cannot_be_purchased(client, auth_headers):
    vehicle = add_vehicle(client, auth_headers, quantity=0)
    response = client.post(f"/api/vehicles/{vehicle['id']}/purchase", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "Vehicle is out of stock"


def test_vehicle_admin_restock_adds_quantity(client, admin_headers):
    vehicle = add_vehicle(client, admin_headers, quantity=0)
    path = f"/api/vehicles/{vehicle['id']}/restock"
    assert client.post(path, headers=admin_headers, json={"quantity": 3}).json()["quantity"] == 3
    assert client.post(path, headers=admin_headers, json={"quantity": 2}).json()["quantity"] == 5


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, "2", None, 2147483648])
def test_vehicle_restock_requires_positive_integer(client, admin_headers, quantity):
    vehicle = add_vehicle(client, admin_headers)
    response = client.post(
        f"/api/vehicles/{vehicle['id']}/restock", headers=admin_headers, json={"quantity": quantity}
    )
    assert response.status_code == 422


def test_vehicle_restock_overflow_returns_conflict(client, admin_headers):
    vehicle = add_vehicle(client, admin_headers, quantity=2147483647)
    response = client.post(
        f"/api/vehicles/{vehicle['id']}/restock", headers=admin_headers, json={"quantity": 1}
    )
    assert response.status_code == 409


@pytest.mark.parametrize("column,value", [("quantity", -1), ("price", 0)])
def test_vehicle_database_constraints_reject_invalid_state(
    client, auth_headers, session, column, value
):
    vehicle = add_vehicle(client, auth_headers)
    with pytest.raises(IntegrityError), session.begin_nested():
        session.execute(
            text(f"UPDATE vehicles SET {column} = :value WHERE id = :id"),
            {"value": value, "id": UUID(vehicle["id"])},
        )
    session.expire_all()
    stored = session.get(Vehicle, UUID(vehicle["id"]))
    assert stored.quantity == 2 and stored.price == Decimal(VEHICLE["price"])
