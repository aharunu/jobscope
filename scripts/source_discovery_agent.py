"""Isolated Codex CLI web research using the user's existing CLI sign-in."""

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError


class AgentCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    board_url: str = Field(max_length=2000)
    chain: list[str] = Field(min_length=1, max_length=10)
    evidence_urls: list[str] = Field(min_length=1, max_length=8)
    explanation: str = Field(min_length=1, max_length=2000)


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    candidates: list[AgentCandidate] = Field(max_length=3)
    unresolved_reason: str = Field(max_length=2000)
    _metrics: dict = PrivateAttr(default_factory=dict)


def read_usage(path):
    """Extract numeric CLI usage only; raw events stay in the disposable directory."""
    usage = {}
    if not path.exists() or path.stat().st_size > 16 * 1024 * 1024:
        return usage
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "turn.completed":
            counters = event.get("usage")
            if not isinstance(counters, dict):
                continue
            for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
                value = counters.get(key)
                if type(value) is int and value >= 0:
                    usage[key] = usage.get(key, 0) + value
    if "input_tokens" in usage and "output_tokens" in usage:
        usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
    return usage


class AgentFailure(Exception):
    """Sanitized process/output failure, suitable for a discovery report."""


def agent_environment():
    # CLI auth reads its own credential store. No app API keys or DB settings
    # are copied to the subprocess; project .env is outside its working root.
    allowed = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "USERPROFILE",
        "HOME",
        "APPDATA",
        "LOCALAPPDATA",
        "TEMP",
        "TMP",
        "CODEX_HOME",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "SSL_CERT_FILE",
    }
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


class CodexDiscoveryAgent:
    def __init__(self, *, model="gpt-6-luna", effort="xhigh", timeout=240):
        self.model, self.effort, self.timeout = model, effort, timeout

    async def research(self, source, issues):
        executable = shutil.which("codex")
        if not executable:
            raise AgentFailure("Codex CLI missing; install Codex and run codex login.")
        instructions = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")
        prompt = (
            instructions
            + "\nTask data:\n"
            + json.dumps(
                {
                    "company": source.company or source.name,
                    "seed_url": source.url,
                    "classical_issues": issues,
                },
                ensure_ascii=False,
            )
        )
        with tempfile.TemporaryDirectory(prefix="jobscope-discovery-") as folder:
            root = Path(folder)
            schema, output = root / "schema.json", root / "result.json"
            events = root / "events.jsonl"
            schema.write_text(
                json.dumps(AgentResult.model_json_schema()), encoding="utf-8"
            )
            command = [
                executable,
                "--search",
                "--ask-for-approval",
                "never",
                "exec",
                "--ignore-user-config",
                "--ephemeral",
                "--json",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--cd",
                str(root),
                "--model",
                self.model,
                "-c",
                f'model_reasoning_effort="{self.effort}"',
                "--output-schema",
                str(schema),
                "--output-last-message",
                str(output),
            ]
            for feature in (
                "shell_tool",
                "apps",
                "multi_agent",
                "computer_use",
                "browser_use",
                "skill_mcp_dependency_install",
            ):
                command.extend(["--disable", feature])
            command.append("-")
            process = None
            events_stream = events.open("wb")
            started = time.monotonic()
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=root,
                    env=agent_environment(),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=events_stream,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(
                    process.communicate(prompt.encode("utf-8")),
                    timeout=self.timeout,
                )
                if process.returncode != 0:
                    raise AgentFailure(
                        f"Codex exited {process.returncode}; check codex login status "
                        f"and model access ({self.model}, {self.effort})."
                    )
                if not output.exists() or output.stat().st_size > 256 * 1024:
                    raise AgentFailure("Codex structured result missing or oversized.")
                answer = AgentResult.model_validate_json(
                    output.read_text(encoding="utf-8")
                )
                events_stream.close()
                answer._metrics = {
                    "wall_seconds": round(time.monotonic() - started, 3),
                    **read_usage(events),
                }
                return answer
            except TimeoutError as exc:
                raise AgentFailure("Codex research timed out.") from exc
            except (OSError, ValidationError, UnicodeError) as exc:
                raise AgentFailure(
                    "Codex execution or structured result invalid."
                ) from exc
            finally:
                if process is not None and process.returncode is None:
                    process.kill()
                    await process.wait()
                events_stream.close()
