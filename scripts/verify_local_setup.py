"""Verify fresh setup, CLI promotion, outages and restart persistence on disposable data only."""

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from app.local_database import initialize, pg, start
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from test_frontend_integration import wait_ready

ROOT = Path(__file__).resolve().parents[1]


def request(path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        "http://127.0.0.1:8002/api" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
    )
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    args = parser.parse_args()
    pg_bin = args.pg_bin.resolve()
    (ROOT / ".tools").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="dealer-persistence-", dir="/tmp"
    ) as directory:
        root = Path(directory)
        shutil.copyfile(ROOT / ".env.example", root / ".env.example")
        api = None
        with (ROOT / ".tools" / "persistence-verification.log").open("w") as logs:
            try:
                initialize(root, pg_bin, 55441)
                settings = dotenv_values(root / ".env")
                env = os.environ | settings
                assert (root / ".env").stat().st_mode & 0o777 == 0o600
                url = settings["DATABASE_URL"]
                engine = create_engine(url)
                with engine.connect() as connection:
                    assert connection.scalar(
                        text(
                            "SELECT NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole FROM pg_roles WHERE rolname = current_user"
                        )
                    )
                engine.dispose()
                alembic = [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini"]
                for command in ["upgrade", "check"]:
                    subprocess.run(
                        [
                            *alembic,
                            command,
                            *(["head"] if command == "upgrade" else []),
                        ],
                        env=env,
                        cwd=ROOT,
                        stdout=logs,
                        stderr=logs,
                        check=True,
                    )
                print(
                    "PASS: fresh SCRAM database, private .env, restricted application role and migrations",
                    flush=True,
                )

                def launch_api():
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "uvicorn",
                            "app.main:app",
                            "--host",
                            "127.0.0.1",
                            "--port",
                            "8002",
                        ],
                        env=env,
                        cwd=ROOT,
                        stdout=logs,
                        stderr=logs,
                    )
                    try:
                        wait_ready("http://127.0.0.1:8002/api/health", process)
                    except Exception:
                        process.terminate()
                        process.wait(timeout=10)
                        raise
                    return process

                api = launch_api()
                account = {
                    "email": "persistence-test@example.com",
                    "password": secrets.token_urlsafe(24),
                }
                assert request("/auth/register", account | {"role": "admin"})[0] == 422
                status, user = request("/auth/register", account)
                assert status == 201 and user["role"] == "user"
                status, login = request("/auth/login", account)
                assert status == 200
                token = login["access_token"]
                status, vehicle = request(
                    "/vehicles",
                    {
                        "make": "Test",
                        "model": "Persistent",
                        "category": "Sedan",
                        "price": "123.45",
                        "quantity": 2,
                    },
                    token,
                )
                assert status == 201
                assert (
                    request(
                        f"/vehicles/{vehicle['id']}/restock", {"quantity": 1}, token
                    )[0]
                    == 403
                )
                command = [
                    sys.executable,
                    "-m",
                    "app.cli",
                    "promote-admin",
                    "--email",
                    account["email"],
                ]
                wrong_url = make_url(url).set(password=secrets.token_hex(32))
                denied = subprocess.run(
                    command,
                    env=env
                    | {"DATABASE_URL": wrong_url.render_as_string(hide_password=False)},
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert (
                    denied.returncode == 1
                    and "Cannot access the database" in denied.stderr
                )
                assert wrong_url.password not in denied.stderr
                assert request("/auth/me", token=token)[1]["role"] == "user"
                for expected in ["Promoted", "already an admin"]:
                    result = subprocess.run(
                        command,
                        env=env,
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    assert result.returncode == 0 and expected in result.stdout
                assert request("/auth/me", token=token)[1]["role"] == "admin"
                assert (
                    request(
                        f"/vehicles/{vehicle['id']}/restock", {"quantity": 1}, token
                    )[1]["quantity"]
                    == 3
                )
                assert (
                    request(f"/vehicles/{vehicle['id']}/purchase", {}, token)[1][
                        "quantity"
                    ]
                    == 2
                )
                # Snapshot every persisted field without logging credentials/password hashes.
                engine = create_engine(url)
                with engine.connect() as connection:
                    original_users = connection.execute(
                        text("SELECT * FROM users ORDER BY id")
                    ).all()
                    original_vehicles = connection.execute(
                        text("SELECT * FROM vehicles ORDER BY id")
                    ).all()
                engine.dispose()
                print(
                    "PASS: ordinary registration, real CLI promotion/rerun and live admin permissions",
                    flush=True,
                )
                api.terminate()
                api.wait(timeout=10)
                try:
                    request("/health")
                    raise AssertionError("API should be stopped")
                except urllib.error.URLError:
                    pass
                api = launch_api()
                assert request("/auth/me", token=token)[1]["role"] == "admin"
                assert request("/vehicles", token=token)[1]["items"][0]["quantity"] == 2
                pg(
                    pg_bin,
                    "pg_ctl",
                    "-D",
                    str(root / ".tools/dev-postgres/data"),
                    "-m",
                    "fast",
                    "-w",
                    "stop",
                )
                assert request("/health")[0] == 503
                assert request("/vehicles", token=token) == (
                    503,
                    {"detail": "Database unavailable. Please try again."},
                )
                start(root, pg_bin)
                assert request("/health")[0] == 200
                assert request("/auth/login", account)[0] == 200
                assert request("/auth/me", token=token)[1]["role"] == "admin"
                engine = create_engine(url)
                with engine.connect() as connection:
                    assert (
                        connection.execute(
                            text("SELECT * FROM users ORDER BY id")
                        ).all()
                        == original_users
                    )
                    assert (
                        connection.execute(
                            text("SELECT * FROM vehicles ORDER BY id")
                        ).all()
                        == original_vehicles
                    )
                engine.dispose()
                print(
                    "PASS: API/database stop-start preserved complete user and vehicle rows, login, role and stock",
                    flush=True,
                )
                print(
                    "PASS: stopped API refused connection; stopped database returned sanitized 503; recovery succeeded",
                    flush=True,
                )
            finally:
                if api is not None and api.poll() is None:
                    api.terminate()
                    api.wait(timeout=10)
                data = root / ".tools/dev-postgres/data"
                if (data / "postmaster.pid").exists():
                    pg(pg_bin, "pg_ctl", "-D", str(data), "-m", "fast", "-w", "stop")
                print(
                    "Stopped disposable verification services; existing databases were not accessed."
                )


if __name__ == "__main__":
    main()
