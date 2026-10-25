"""Launch real PostgreSQL, FastAPI and Vite for browser tests, then clean up.

All database state and credentials are disposable. Requires installed Node and Chromium.
Usage: backend/.venv/bin/python scripts/test_frontend_integration.py --pg-bin .tools/postgres/bin
"""

import argparse
import os
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from app.core.security import hash_password
from app.models import Role, User
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]


def run(command, **kwargs):
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def wait_ready(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(f"Service exited before ready: {url}")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Service did not become ready: {url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    args = parser.parse_args()
    pg_bin = args.pg_bin.resolve()
    processes = []
    (ROOT / ".tools").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dealer-browser-", dir="/tmp") as directory:
        temp = Path(directory)
        data = temp / "data"
        started = False
        with (ROOT / ".tools" / "browser-services.log").open("w") as logs:
            try:
                run(
                    [
                        pg_bin / "initdb",
                        "-D",
                        data,
                        "-U",
                        "dealership_test",
                        "-A",
                        "trust",
                        "--no-locale",
                        "-E",
                        "UTF8",
                    ],
                    stdout=logs,
                )
                run(
                    [
                        pg_bin / "pg_ctl",
                        "-D",
                        data,
                        "-l",
                        temp / "postgres.log",
                        "-o",
                        f"-k {temp} -h '' -p 55440",
                        "-w",
                        "start",
                    ],
                    stdout=logs,
                )
                started = True
                run(
                    [
                        pg_bin / "createdb",
                        "-h",
                        temp,
                        "-p",
                        "55440",
                        "-U",
                        "dealership_test",
                        "browser_test",
                    ]
                )
                database_url = URL.create(
                    "postgresql+psycopg",
                    username="dealership_test",
                    database="browser_test",
                    query={"host": str(temp), "port": "55440"},
                ).render_as_string(hide_password=False)
                backend_env = os.environ | {
                    "DATABASE_URL": database_url,
                    "JWT_SECRET_KEY": secrets.token_hex(32),
                    "CORS_ORIGINS": '["http://127.0.0.1:5175"]',
                }
                run(
                    [
                        sys.executable,
                        "-m",
                        "alembic",
                        "-c",
                        "backend/alembic.ini",
                        "upgrade",
                        "head",
                    ],
                    env=backend_env,
                )
                admin_email, admin_password = (
                    "browser-admin@example.com",
                    secrets.token_urlsafe(24),
                )
                engine = create_engine(database_url)
                with Session(engine) as session:
                    session.add(
                        User(
                            email=admin_email,
                            name="Inventory Admin",
                            role=Role.ADMIN,
                            password_hash=hash_password(admin_password),
                        )
                    )
                    session.commit()
                engine.dispose()
                api = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8001",
                    ],
                    cwd=ROOT,
                    env=backend_env,
                    stdout=logs,
                    stderr=logs,
                )
                processes.append(api)
                wait_ready("http://127.0.0.1:8001/api/health", api)
                frontend_env = os.environ | {
                    "API_PROXY_TARGET": "http://127.0.0.1:8001",
                    "VITE_API_BASE_URL": "/api",
                }
                vite = subprocess.Popen(
                    [
                        "node",
                        "node_modules/vite/bin/vite.js",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "5175",
                    ],
                    cwd=ROOT / "frontend",
                    env=frontend_env,
                    stdout=logs,
                    stderr=logs,
                )
                processes.append(vite)
                wait_ready("http://127.0.0.1:5175", vite)
                # Verify direct-origin CORS independently of the browser's same-origin Vite proxy.
                request = urllib.request.Request(
                    "http://127.0.0.1:8001/api/auth/login",
                    method="OPTIONS",
                    headers={
                        "Origin": "http://127.0.0.1:5175",
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "content-type,authorization",
                    },
                )
                with urllib.request.urlopen(request) as response:
                    assert (
                        response.headers["Access-Control-Allow-Origin"]
                        == "http://127.0.0.1:5175"
                    )
                print(
                    "PASS: live API health, Vite startup and CORS preflight", flush=True
                )
                browser_env = os.environ | {
                    "E2E_ADMIN_EMAIL": admin_email,
                    "E2E_ADMIN_PASSWORD": admin_password,
                    "E2E_BASE_URL": "http://127.0.0.1:5175",
                    "E2E_SCREENSHOT_DIR": str(ROOT / ".tools" / "browser-screenshots"),
                }
                run(["npm", "--prefix", "frontend", "run", "test:e2e"], env=browser_env)
            finally:
                for process in reversed(processes):
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                if started:
                    run(
                        [pg_bin / "pg_ctl", "-D", data, "-m", "fast", "-w", "stop"],
                        stdout=logs,
                    )
                print(
                    "Stopped temporary frontend, API and PostgreSQL services.",
                    flush=True,
                )


if __name__ == "__main__":
    main()
