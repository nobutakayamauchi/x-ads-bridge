from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from operation_protocol import OperationProtocolError, execute


RESULT_PATH = Path("result.md")
MAX_COMMENT_CHARS = 55000


def _load_event() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "").strip()
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


def _write_result(title: str, payload: object) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(rendered) > MAX_COMMENT_CHARS:
        rendered = rendered[:MAX_COMMENT_CHARS] + "\n... [truncated]"
    RESULT_PATH.write_text(
        f"### {title}\n\n```json\n{rendered}\n```\n",
        encoding="utf-8",
    )


def main() -> int:
    try:
        event = _load_event()
        issue = event.get("issue") or {}
        event_action = str(event.get("action") or "").strip().lower()
        owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
        author = ((issue.get("user") or {}).get("login") or "").strip()
        title = str(issue.get("title") or "")

        if not owner or author != owner:
            raise RuntimeError(f"unauthorized issue author: {author or '<unknown>'}")
        if not title.startswith("[xop]"):
            raise RuntimeError("ignored: issue title must start with [xop]")
        if event_action != "opened":
            raise RuntimeError(
                "operation protocol actions require a newly opened issue; "
                "reopened issues are never accepted"
            )

        os.environ["XADS_EVENT_ACTION"] = "opened"
        command = _parse_command(str(issue.get("body") or ""))
        result = execute(command)
        _write_result("X Ads Operation Protocol 01", result)
        return 0
    except (OperationProtocolError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        _write_result("X Ads Operation Protocol 01 blocked/failed", {
            "ok": False,
            "error": str(exc),
        })
        return 1
    except Exception as exc:
        _write_result("X Ads Operation Protocol 01 unexpected failure", {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        })
        return 1


if __name__ == "__main__":
    sys.exit(main())
