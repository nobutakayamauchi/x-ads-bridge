from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from requests_oauthlib import OAuth1

BASE_URL = os.getenv("XADS_BASE_URL", "https://ads-api.x.com").rstrip("/")
API_VERSION = os.getenv("XADS_API_VERSION", "12")
DEFAULT_ACCOUNT_ID = os.getenv("XADS_ACCOUNT_ID", "").strip()
RESULT_PATH = Path("result.md")


class WebEventBridgeError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise WebEventBridgeError(f"missing required secret/env: {name}")
    return value


def _auth() -> OAuth1:
    return OAuth1(
        _required_env("XADS_CONSUMER_KEY"),
        _required_env("XADS_CONSUMER_SECRET"),
        _required_env("XADS_ACCESS_TOKEN"),
        _required_env("XADS_ACCESS_TOKEN_SECRET"),
    )


def _read_command() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH", "").strip()
    if not event_path:
        raise WebEventBridgeError("GITHUB_EVENT_PATH is not configured")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    body = str(issue.get("body") or "").strip()
    if not body:
        raise WebEventBridgeError("issue body must contain a JSON command")
    try:
        command = json.loads(body)
    except json.JSONDecodeError as exc:
        raise WebEventBridgeError("issue body must be valid JSON") from exc
    if not isinstance(command, dict):
        raise WebEventBridgeError("issue body JSON must be an object")
    return command


def _account_id(command: dict[str, Any]) -> str:
    account_id = str(command.get("account_id") or DEFAULT_ACCOUNT_ID).strip()
    if not account_id:
        raise WebEventBridgeError("account_id is required")
    return account_id


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(
        f"{BASE_URL}/{API_VERSION}/{path.lstrip('/')}",
        params=params,
        auth=_auth(),
        timeout=45,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text[:4000]}
    if not response.ok:
        raise WebEventBridgeError(
            f"X Ads API {response.status_code}: {json.dumps(payload, ensure_ascii=False)[:4000]}"
        )
    if not isinstance(payload, dict):
        raise WebEventBridgeError("X Ads API response must be an object")
    return payload


def _execute(command: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    action = str(command.get("action") or "").strip()
    account_id = _account_id(command)

    if action == "list_web_event_tags":
        payload = _get(
            f"accounts/{account_id}/web_event_tags",
            {"with_deleted": str(bool(command.get("with_deleted", False))).lower()},
        )
        return "X Ads web event tags result", payload

    if action == "list_targeting_criteria":
        line_item_ids = command.get("line_item_ids")
        if isinstance(line_item_ids, list):
            values = [str(value).strip() for value in line_item_ids if str(value).strip()]
            line_item_ids = ",".join(values)
        else:
            line_item_ids = str(line_item_ids or "").strip()
        if not line_item_ids:
            raise WebEventBridgeError("line_item_ids is required")
        payload = _get(
            f"accounts/{account_id}/targeting_criteria",
            {
                "line_item_ids": line_item_ids,
                "count": int(command.get("count") or 200),
                "with_deleted": str(bool(command.get("with_deleted", False))).lower(),
            },
        )
        return "X Ads targeting criteria result", payload

    raise WebEventBridgeError(
        "supported actions: list_web_event_tags, list_targeting_criteria"
    )


def _write_result(title: str, payload: dict[str, Any]) -> None:
    RESULT_PATH.write_text(
        f"### {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )


def main() -> int:
    try:
        command = _read_command()
        title, payload = _execute(command)
        _write_result(title, payload)
        return 0
    except Exception as exc:
        _write_result("X Ads inspection failed", {"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
