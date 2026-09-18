"""JobScope developer task automation helper.

Provides cross-platform shortcuts for common development workflows
without external task-runner dependencies.
"""

import argparse
import subprocess
import sys


def run_command(cmd: list[str]) -> int:
    """Execute a CLI command within the current Python environment."""
    print(f"--> Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def cmd_test(args: argparse.Namespace) -> int:
    """Run pytest suite with optional arguments."""
    cmd = [sys.executable, "-m", "pytest", "-v"] + (args.extra_args or [])
    return run_command(cmd)


def cmd_lint(args: argparse.Namespace) -> int:
    """Run ruff linter checks."""
    cmd = [sys.executable, "-m", "ruff", "check", "."]
    if args.fix:
        cmd.append("--fix")
    return run_command(cmd)


def cmd_format(args: argparse.Namespace) -> int:
    """Run ruff formatter."""
    cmd = [sys.executable, "-m", "ruff", "format"]
    if args.check:
        cmd.append("--check")
    cmd.append(".")
    return run_command(cmd)


def cmd_run(args: argparse.Namespace) -> int:
    """Start local uvicorn development server."""
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.interfaces.api.main:app",
        "--reload",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    return run_command(cmd)


def cmd_migrate(args: argparse.Namespace) -> int:
    """Run database migration commands via Alembic."""
    cmd = [sys.executable, "-m", "alembic", "upgrade", args.revision]
    return run_command(cmd)


def cmd_check(args: argparse.Namespace) -> int:
    """Run full quality suite: format check, lint, and tests."""
    print("=== Step 1: Format Check ===")
    code = run_command([sys.executable, "-m", "ruff", "format", "--check", "."])
    if code != 0:
        return code

    print("\n=== Step 2: Lint Check ===")
    code = run_command([sys.executable, "-m", "ruff", "check", "."])
    if code != 0:
        return code

    print("\n=== Step 3: Test Suite ===")
    return run_command([sys.executable, "-m", "pytest", "-v"])


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="JobScope Developer Command Runner",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # test
    p_test = subparsers.add_parser("test", help="Run automated tests")
    p_test.set_defaults(func=cmd_test)

    # lint
    p_lint = subparsers.add_parser("lint", help="Run ruff linter")
    p_lint.add_argument("--fix", action="store_true", help="Automatically fix issues")
    p_lint.set_defaults(func=cmd_lint)

    # format
    p_fmt = subparsers.add_parser("format", help="Run ruff code formatter")
    p_fmt.add_argument("--check", action="store_true", help="Check formatting only")
    p_fmt.set_defaults(func=cmd_format)

    # run
    p_run = subparsers.add_parser("run", help="Start FastAPI development server")
    p_run.add_argument("--host", default="127.0.0.1", help="Host address")
    p_run.add_argument("--port", type=int, default=8000, help="Port number")
    p_run.set_defaults(func=cmd_run)

    # migrate
    p_mig = subparsers.add_parser("migrate", help="Run Alembic migrations")
    p_mig.add_argument(
        "--revision", default="head", help="Target revision (default: head)"
    )
    p_mig.set_defaults(func=cmd_migrate)

    # check
    p_chk = subparsers.add_parser("check", help="Run format check, lint, and tests")
    p_chk.set_defaults(func=cmd_check)

    return parser


def parse_dev_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse developer CLI arguments, forwarding extra test arguments if present."""
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    if args.command == "test":
        args.extra_args = unknown
    elif unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")
    return args


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_dev_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
