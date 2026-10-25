"""Create/manage this checkout's dedicated, persistent, loopback-only PostgreSQL cluster.

Never adopts, resets or deletes a cluster. Existing .env/data make init refuse to proceed.
Use a regular OS account, not root. PostgreSQL binaries must already be installed.
"""

import argparse
import os
import secrets
import shlex
import socket
import subprocess
import sys
from pathlib import Path

import psycopg
from psycopg import sql

from app.core.config import ENV_FILE


class SetupError(Exception):
    pass


def private_file(path: Path, value: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(value)


def pg(pg_bin: Path, *arguments: str) -> None:
    subprocess.run([str(pg_bin / arguments[0]), *arguments[1:]], check=True, capture_output=True)


def cluster_path(root: Path) -> Path:
    return root / ".tools" / "dev-postgres"


def start(root: Path, pg_bin: Path) -> None:
    directory = cluster_path(root)
    if not (directory / "data" / "PG_VERSION").is_file():
        raise SetupError(
            "No managed cluster found; initialize it first or use your existing server."
        )
    port = int((directory / "port").read_text())
    pg(
        pg_bin,
        "pg_ctl",
        "-D",
        str(directory / "data"),
        "-l",
        str(directory / "postgres.log"),
        "-o",
        shlex.join(["-h", "127.0.0.1", "-k", "", "-p", str(port)]),
        "-w",
        "start",
    )


def initialize(root: Path, pg_bin: Path, port: int) -> None:
    env = root / ".env"
    directory = cluster_path(root)
    if env.exists() or env.is_symlink() or directory.exists() or directory.is_symlink():
        raise SetupError(
            "Refusing to overwrite existing .env or managed database files. "
            "Use start or configure the existing server manually."
        )
    # Refuse occupied ports before writing files. pg_ctl also fails if a later race takes the port.
    with socket.socket() as check:
        check.bind(("127.0.0.1", port))
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir(mode=0o700)
    password, operator_password = secrets.token_hex(32), secrets.token_hex(32)
    private_file(directory / "operator-password", operator_password + "\n")
    private_file(directory / "port", str(port))
    pg(
        pg_bin,
        "initdb",
        "-D",
        str(directory / "data"),
        "-U",
        "dealership_operator",
        "-A",
        "scram-sha-256",
        "--pwfile",
        str(directory / "operator-password"),
        "--no-locale",
        "-E",
        "UTF8",
    )
    start(root, pg_bin)
    try:
        with psycopg.connect(
            host="127.0.0.1",
            port=port,
            user="dealership_operator",
            password=operator_password,
            dbname="postgres",
            autocommit=True,
        ) as connection:
            connection.execute(
                sql.SQL(
                    "CREATE ROLE dealership LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}"
                ).format(sql.Literal(password))
            )
            connection.execute("CREATE DATABASE dealership OWNER dealership")
        example = (root / ".env.example").read_text()
        replacements = {
            "POSTGRES_DB": "dealership",
            "POSTGRES_USER": "dealership",
            "POSTGRES_PASSWORD": password,
            "POSTGRES_PORT": str(port),
            "DATABASE_URL": f"postgresql+psycopg://dealership:{password}@127.0.0.1:{port}/dealership",
            "JWT_SECRET_KEY": secrets.token_hex(32),
        }
        lines = [
            f"{line.split('=', 1)[0]}={replacements[line.split('=', 1)[0]]}"
            if line.split("=", 1)[0] in replacements
            else line
            for line in example.splitlines()
        ]
        private_file(env, "\n".join(lines) + "\n")
    except Exception:
        pg(pg_bin, "pg_ctl", "-D", str(directory / "data"), "-m", "fast", "-w", "stop")
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "start", "stop", "status"])
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument(
        "--port", type=int, default=55432, help="Port for init only (default 55432)"
    )
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be between 1024 and 65535")
    pg_bin = args.pg_bin.resolve()
    if not all((pg_bin / name).is_file() for name in ["initdb", "pg_ctl"]):
        parser.error("--pg-bin must contain PostgreSQL initdb and pg_ctl")
    root = ENV_FILE.parent
    try:
        if args.action == "init":
            initialize(root, pg_bin, args.port)
            print(
                "Created persistent PostgreSQL and a private .env. "
                "No application accounts were created."
            )
            print("Next: python -m alembic -c backend/alembic.ini upgrade head")
        elif args.action == "start":
            start(root, pg_bin)
            print("PostgreSQL started; existing data retained.")
        else:
            directory = cluster_path(root)
            if not (directory / "data" / "PG_VERSION").is_file():
                raise SetupError("No managed cluster found.")
            arguments = ["pg_ctl", "-D", str(directory / "data")]
            arguments.extend(["-m", "fast", "-w", "stop"] if args.action == "stop" else ["status"])
            pg(pg_bin, *arguments)
            print(
                "PostgreSQL stopped; data retained."
                if args.action == "stop"
                else "PostgreSQL is running."
            )
        return 0
    except SetupError as exc:
        print(str(exc), file=sys.stderr)
    except (OSError, ValueError, psycopg.Error, subprocess.CalledProcessError):
        print(
            "Database command failed (or status is stopped). Check binaries, port and "
            ".tools/dev-postgres/postgres.log locally. Existing files were preserved; "
            "no secrets were printed.",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
