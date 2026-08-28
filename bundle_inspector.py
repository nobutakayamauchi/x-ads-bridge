from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import bridge

RESULT_PATH = Path("result.md")
MAX_COMMENT_CHARS = 55000


def _load_event() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is missing")
    return json.loads(Path(event_path).read_text(encoding="utf-8"))


def _parse_command(body: str) -> dict:
    text = (body or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("issue body must be a JSON object")
    return parsed


def _write_result(payload: object) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(rendered) > MAX_COMMENT_CHARS:
        rendered = rendered[:MAX_COMMENT_CHARS] + "\n... [truncated]"
    RESULT_PATH.write_text(
        "### X Ads read-only bundle inspector\n\n"
        "`read_only=true` `write_executed=false`\n\n"
        f"```json\n{rendered}\n```\n",
        encoding="utf-8",
    )


def inspect_line_item_bundle(command: dict) -> dict:
    account_id = str(command.get("account_id") or bridge.DEFAULT_ACCOUNT_ID).strip()
    line_item_id = str(command.get("line_item_id") or "").strip()
    if not account_id:
        raise ValueError("account_id is required")
    if not line_item_id:
        raise ValueError("line_item_id is required")

    line_item = bridge._request("GET", f"accounts/{account_id}/line_items/{line_item_id}")
    line_data = line_item.get("data")
    if not isinstance(line_data, dict):
        raise RuntimeError("line item response missing data object")
    campaign_id = str(line_data.get("campaign_id") or "").strip()
    if not campaign_id:
        raise RuntimeError("line item response missing campaign_id")

    campaign = bridge._request("GET", f"accounts/{account_id}/campaigns/{campaign_id}")
    targeting = bridge._request(
        "GET",
        f"accounts/{account_id}/targeting_criteria",
        params={"line_item_ids": line_item_id, "count": 1000},
    )
    promoted_tweets = bridge._request(
        "GET",
        f"accounts/{account_id}/promoted_tweets",
        params={"line_item_ids": line_item_id, "count": 1000},
    )

    return {
        "ok": True,
        "read_only": True,
        "write_executed": False,
        "account_id": account_id,
        "line_item_id": line_item_id,
        "campaign_id": campaign_id,
        "line_item": line_item,
        "campaign": campaign,
        "targeting": targeting,
        "promoted_tweets": promoted_tweets,
    }


def main() -> int:
    try:
        event = _load_event()
        issue = event.get("issue") or {}
        owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
        author = ((issue.get("user") or {}).get("login") or "").strip()
        title = str(issue.get("title") or "")
        if not owner or author != owner:
            raise RuntimeError(f"unauthorized issue author: {author or '<unknown>'}")
        if not title.startswith("[xinspect]"):
            raise RuntimeError("ignored: issue title must start with [xinspect]")

        command = _parse_command(str(issue.get("body") or ""))
        if str(command.get("action") or "") != "inspect_line_item_bundle":
            raise ValueError("supported action: inspect_line_item_bundle")
        _write_result(inspect_line_item_bundle(command))
        return 0
    except Exception as exc:
        _write_result({"ok": False, "read_only": True, "write_executed": False, "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    sys.exit(main())
