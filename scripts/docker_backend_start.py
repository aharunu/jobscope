"""Container-only database configuration and fail-fast migration startup."""

import os
import subprocess
import sys
from urllib.parse import quote


def main() -> None:
    # Build from the same raw credentials as PostgreSQL, safely URL-encoding them.
    # Never load the native DATABASE_URL or connect to the host database here.
    user = quote(os.environ["POSTGRES_USER"], safe="")
    password = quote(os.environ["POSTGRES_PASSWORD"], safe="")
    database = quote(os.environ["POSTGRES_DB"], safe="")
    os.environ["DATABASE_URL"] = (
        f"postgresql+asyncpg://{user}:{password}@db:5432/{database}"
    )
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    command = sys.argv[1:]
    if not command:
        raise SystemExit("A backend command is required")
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
