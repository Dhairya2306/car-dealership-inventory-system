"""Run migrations and pytest in a fresh, temporary PostgreSQL cluster (no Docker needed).

Usage: backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin
The cluster has no TCP listener; its Unix socket is inside a private temporary directory.
No DATABASE_URL, .env credentials, existing PostgreSQL instance or database is used.
"""

import argparse
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from app.core.security import hash_password
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]


def run(arguments, **kwargs):
    print("RUN:", " ".join(str(argument) for argument in arguments), flush=True)
    subprocess.run(arguments, check=True, cwd=ROOT, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    args, pytest_args = parser.parse_known_args()
    pg_bin = args.pg_bin.resolve()
    for executable in ("initdb", "pg_ctl", "createdb"):
        if not (pg_bin / executable).is_file():
            parser.error(f"PostgreSQL executable missing: {pg_bin / executable}")

    # Short paths matter for PostgreSQL's Unix-domain socket path-length limit on macOS.
    with tempfile.TemporaryDirectory(prefix="dealer-test-", dir="/tmp") as temp:
        directory = Path(temp)
        data = directory / "data"
        log = directory / "postgres.log"
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
            ]
        )
        started = False
        try:
            run(
                [
                    pg_bin / "pg_ctl",
                    "-D",
                    data,
                    "-l",
                    log,
                    "-o",
                    f"-k {directory} -h '' -p 55439",
                    "-w",
                    "start",
                ]
            )
            started = True
            run(
                [
                    pg_bin / "createdb",
                    "-h",
                    directory,
                    "-p",
                    "55439",
                    "-U",
                    "dealership_test",
                    "dealership_auth_test",
                ]
            )
            url = URL.create(
                "postgresql+psycopg",
                username="dealership_test",
                database="dealership_auth_test",
                query={"host": str(directory), "port": "55439"},
            ).render_as_string(hide_password=False)
            env = os.environ.copy()
            env.update(
                DATABASE_URL=url,
                TEST_DATABASE_URL=url,
                JWT_SECRET_KEY=secrets.token_hex(32),
                JWT_ALGORITHM="HS256",
            )
            alembic = [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini"]
            run([*alembic, "upgrade", "0001_create_users"], env=env)
            engine = create_engine(url)
            try:
                sentinel_id = uuid4()
                lookup_user = text("SELECT * FROM users WHERE id = :id")
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "INSERT INTO users (id, email, password_hash) VALUES (:id, :email, :hash)"
                        ),
                        {
                            "id": sentinel_id,
                            "email": "migration-check@example.com",
                            "hash": hash_password(secrets.token_hex(32)),
                        },
                    )
                    original_user = connection.execute(
                        lookup_user, {"id": sentinel_id}
                    ).one()
                run([*alembic, "upgrade", "head"], env=env)
                run([*alembic, "current"], env=env)
                run([*alembic, "check"], env=env)
                with engine.begin() as connection:
                    assert (
                        connection.execute(lookup_user, {"id": sentinel_id}).one()
                        == original_user
                    )
                    assert connection.scalar(text("SELECT count(*) FROM vehicles")) == 0
                run([*alembic, "downgrade", "0001_create_users"], env=env)
                with engine.begin() as connection:
                    assert (
                        connection.execute(lookup_user, {"id": sentinel_id}).one()
                        == original_user
                    )
                    assert (
                        connection.scalar(text("SELECT to_regclass('public.vehicles')"))
                        is None
                    )
                print(
                    "PASS: existing user preserved across vehicle upgrade and downgrade",
                    flush=True,
                )
                run([*alembic, "upgrade", "head"], env=env)
                run([*alembic, "downgrade", "base"], env=env)
                with engine.begin() as connection:
                    assert (
                        connection.scalar(text("SELECT to_regclass('public.users')"))
                        is None
                    )
                    assert (
                        connection.scalar(text("SELECT to_regclass('public.vehicles')"))
                        is None
                    )
                run([*alembic, "upgrade", "head"], env=env)
            finally:
                engine.dispose()
            # The tests forbid DATABASE_URL equality and only consume TEST_DATABASE_URL.
            test_env = env.copy()
            test_env.pop("DATABASE_URL")
            run(
                [sys.executable, "-m", "pytest", "backend/tests", *pytest_args],
                env=test_env,
            )
        finally:
            if started:
                run([pg_bin / "pg_ctl", "-D", data, "-m", "fast", "-w", "stop"])


if __name__ == "__main__":
    main()
