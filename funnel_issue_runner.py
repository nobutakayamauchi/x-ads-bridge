from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from funnel_bridge import FunnelBridgeError, execute

RESULT_PATH = Path("result.md")
MAX_COMMENT_CHARS = 55000


def _load_event() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is missing")
    return json.loads(Path(event_path).read_text(encoding="utf-8"))


def _parse_command(body: str) -> dict:
    text = (body or "").strip()
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced:
        text = fenced.group(1).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("issue body must be a JSON object")
    return parsed


def _write_result(title: str, command: dict | None, payload: object) -> None:
    command_name = command.get("action") if isinstance(command, dict) else None
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(rendered) > MAX_COMMENT_CHARS:
        rendered = rendered[:MAX_COMMENT_CHARS] + "\n... [truncated]"
    text = f"### {title}\n\n"
    if command_name:
        text += f"Action: `{command_name}`\n\n"
    text += f"```json\n{rendered}\n```\n"
    RESULT_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    command = None
    try:
        event = _load_event()
        issue = event.get("issue") or {}
        owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
        author = ((issue.get("user") or {}).get("login") or "").strip()
        title = str(issue.get("title") or "")

        if not owner or author != owner:
            raise RuntimeError(f"unauthorized issue author: {author or '<unknown>'}")
        if not title.startswith("[funnel]"):
            raise RuntimeError("ignored: issue title must start with [funnel]")

        command = _parse_command(str(issue.get("body") or ""))
        result = execute(command)
        _write_result("Funnel audit result", command, result)
        return 0
    except (FunnelBridgeError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        _write_result(
            "Funnel audit blocked/failed",
            command,
            {"ok": False, "error": str(exc)},
        )
        return 1
    except Exception as exc:
        _write_result(
            "Funnel audit unexpected failure",
            command,
            {"ok": False, "error": type(exc).__name__, "message": str(exc)},
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
