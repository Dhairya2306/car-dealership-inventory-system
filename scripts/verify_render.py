"""Verify documented Render commands locally, without accessing Render or existing databases.

Copies backend sources into a disposable directory, installs locked production dependencies,
then runs migrations and Uvicorn against a new local PostgreSQL cluster. Requires local uv/PG.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from app.local_database import initialize, pg
from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from test_frontend_integration import wait_ready

ROOT = Path(__file__).resolve().parents[1]
BUILD = ["uv", "sync", "--locked", "--no-dev"]
MIGRATE = [".venv/bin/python", "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"]
START = '.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv-bin", type=Path, required=True)
    parser.add_argument("--pg-bin", type=Path, required=True)
    args = parser.parse_args()
    uv_bin, pg_bin = args.uv_bin.resolve(), args.pg_bin.resolve()
    (ROOT / ".tools").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dealer-render-", dir="/tmp") as directory:
        root = Path(directory)
        project = root / "backend"
        project.mkdir()
        for name in ["app", "migrations"]:
            shutil.copytree(
                ROOT / "backend" / name,
                project / name,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        for name in ["pyproject.toml", "uv.lock", "alembic.ini"]:
            shutil.copyfile(ROOT / "backend" / name, project / name)
        database = root / "database"
        database.mkdir()
        shutil.copyfile(ROOT / ".env.example", database / ".env.example")
        api = None
        with (ROOT / ".tools" / "render-verification.log").open("w") as logs:
            try:
                # Pin the local interpreter to the same tested version configured on Render.
                env = os.environ.copy()
                for name in ["VIRTUAL_ENV", "DATABASE_URL", "JWT_SECRET_KEY"]:
                    env.pop(name, None)
                env.update(UV_PYTHON=sys.executable, UV_PROJECT_ENVIRONMENT=".venv")
                print("RUN (isolated backend root):", " ".join(BUILD), flush=True)
                subprocess.run(
                    [str(uv_bin), *BUILD[1:]],
                    cwd=project,
                    env=env,
                    stdout=logs,
                    stderr=logs,
                    check=True,
                )
                subprocess.run(
                    [
                        ".venv/bin/python",
                        "-c",
                        (
                            "import importlib.util; import app, alembic, psycopg, uvicorn; "
                            "assert importlib.util.find_spec('pytest') is None"
                        ),
                    ],
                    cwd=project,
                    env=env,
                    check=True,
                )
                assert (project / "uv.lock").read_bytes() == (
                    ROOT / "backend/uv.lock"
                ).read_bytes()
                print(
                    "PASS: fresh locked production install; dev extras absent; lock unchanged",
                    flush=True,
                )
                initialize(database, pg_bin, 55442)
                values = dotenv_values(database / ".env")
                env.update(values)
                # Use Render's ordinary postgres URL style, not the SQLAlchemy-specific scheme.
                env["DATABASE_URL"] = (
                    make_url(values["DATABASE_URL"])
                    .set(drivername="postgresql")
                    .render_as_string(hide_password=False)
                )
                env.update(PORT="8003", CORS_ORIGINS='["https://inventory.example"]')
                assert not (root / ".env").exists()
                print("RUN (isolated backend root):", " ".join(MIGRATE), flush=True)
                subprocess.run(
                    MIGRATE, cwd=project, env=env, stdout=logs, stderr=logs, check=True
                )
                subprocess.run(
                    [".venv/bin/python", "-m", "alembic", "-c", "alembic.ini", "check"],
                    cwd=project,
                    env=env,
                    stdout=logs,
                    stderr=logs,
                    check=True,
                )
                print("RUN (isolated backend root):", START, flush=True)
                api = subprocess.Popen(
                    ["sh", "-c", "exec " + START],
                    cwd=project,
                    env=env,
                    stdout=logs,
                    stderr=logs,
                )
                wait_ready("http://127.0.0.1:8003/api/health", api)
                request = urllib.request.Request(
                    "http://127.0.0.1:8003/api/vehicles",
                    method="OPTIONS",
                    headers={
                        "Origin": "https://inventory.example",
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "authorization,content-type",
                    },
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    assert response.status == 200
                    assert (
                        response.headers["Access-Control-Allow-Origin"]
                        == "https://inventory.example"
                    )
                print(
                    "PASS: migrations, hosted URL format, env-only secrets, PORT binding, health and HTTPS-origin CORS",
                    flush=True,
                )
            finally:
                if api is not None:
                    api.terminate()
                    api.wait(timeout=10)
                data = database / ".tools/dev-postgres/data"
                if (data / "postmaster.pid").exists():
                    pg(pg_bin, "pg_ctl", "-D", str(data), "-m", "fast", "-w", "stop")
                print(
                    "Stopped local verification services; no hosted resources accessed."
                )


if __name__ == "__main__":
    main()
