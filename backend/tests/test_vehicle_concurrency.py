"""Real requests with separate PostgreSQL transactions; no session dependency overrides."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import sessionmaker

from app.application import create_app
from app.models import Role, User, Vehicle


@pytest.fixture
def real_inventory(engine, settings):
    application = create_app(settings)
    application.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    user_id = vehicle_id = None
    try:
        with TestClient(application) as client:
            credentials = {
                "email": "stock-race@example.com",
                "password": "Stock race test password!",
            }
            registration = client.post("/api/auth/register", json=credentials)
            assert registration.status_code == 201
            user_id = UUID(registration.json()["id"])
            token = client.post("/api/auth/login", json=credentials).json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            # Admin role is provisioned only in this temporary test database.
            with engine.begin() as connection:
                connection.execute(update(User).where(User.id == user_id).values(role=Role.ADMIN))
            creation = client.post(
                "/api/vehicles",
                headers=headers,
                json={
                    "make": "Toyota",
                    "model": "Corolla",
                    "category": "Sedan",
                    "price": "24500.25",
                    "quantity": 1,
                },
            )
            assert creation.status_code == 201
            vehicle_id = UUID(creation.json()["id"])
            yield client, headers, vehicle_id
    finally:
        with engine.begin() as connection:
            if vehicle_id is not None:
                connection.execute(delete(Vehicle).where(Vehicle.id == vehicle_id))
            if user_id is not None:
                connection.execute(delete(User).where(User.id == user_id))


def run_together(actions):
    barrier = Barrier(len(actions))

    def perform(action):
        barrier.wait(timeout=10)
        return action()

    with ThreadPoolExecutor(max_workers=len(actions)) as executor:
        futures = [executor.submit(perform, action) for action in actions]
        return [future.result(timeout=20) for future in futures]


@pytest.mark.parametrize("starting_stock", [1, 3])
def test_concurrent_vehicle_purchases_never_oversell(real_inventory, engine, starting_stock):
    client, headers, vehicle_id = real_inventory
    path = f"/api/vehicles/{vehicle_id}"
    if starting_stock > 1:
        assert (
            client.post(
                path + "/restock", headers=headers, json={"quantity": starting_stock - 1}
            ).status_code
            == 200
        )
    responses = run_together(
        [lambda: client.post(path + "/purchase", headers=headers) for _ in range(8)]
    )
    assert sum(response.status_code == 200 for response in responses) == starting_stock
    assert sum(response.status_code == 409 for response in responses) == 8 - starting_stock
    assert sorted(
        response.json()["quantity"] for response in responses if response.status_code == 200
    ) == list(range(starting_stock))
    with engine.connect() as connection:
        assert connection.scalar(select(Vehicle.quantity).where(Vehicle.id == vehicle_id)) == 0


def test_concurrent_vehicle_restocks_do_not_lose_increments(real_inventory, engine):
    client, headers, vehicle_id = real_inventory
    responses = run_together(
        [
            lambda amount=amount: client.post(
                f"/api/vehicles/{vehicle_id}/restock", headers=headers, json={"quantity": amount}
            )
            for amount in [1, 2, 3, 4]
        ]
    )
    assert all(response.status_code == 200 for response in responses)
    with engine.connect() as connection:
        assert connection.scalar(select(Vehicle.quantity).where(Vehicle.id == vehicle_id)) == 11


def test_concurrent_vehicle_details_edit_does_not_restore_purchased_stock(real_inventory, engine):
    client, headers, vehicle_id = real_inventory
    path = f"/api/vehicles/{vehicle_id}"
    responses = run_together(
        [
            lambda: client.post(path + "/purchase", headers=headers),
            lambda: client.put(
                path,
                headers=headers,
                json={
                    "make": "Honda",
                    "model": "Civic",
                    "category": "Sedan",
                    "price": "25000",
                },
            ),
        ]
    )
    assert all(response.status_code == 200 for response in responses)
    with engine.connect() as connection:
        row = connection.execute(
            select(Vehicle.quantity, Vehicle.make).where(Vehicle.id == vehicle_id)
        ).one()
        assert row.quantity == 0 and row.make == "Honda"


def test_concurrent_vehicle_purchase_and_restock_preserve_total(real_inventory, engine):
    client, headers, vehicle_id = real_inventory
    path = f"/api/vehicles/{vehicle_id}"
    assert client.post(path + "/restock", headers=headers, json={"quantity": 9}).status_code == 200
    actions = [lambda: client.post(path + "/purchase", headers=headers) for _ in range(4)]
    actions += [
        lambda: client.post(path + "/restock", headers=headers, json={"quantity": 2})
        for _ in range(4)
    ]
    assert all(response.status_code == 200 for response in run_together(actions))
    with engine.connect() as connection:
        assert connection.scalar(select(Vehicle.quantity).where(Vehicle.id == vehicle_id)) == 14
