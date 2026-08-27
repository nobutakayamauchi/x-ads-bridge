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


def _request_tags(command: dict[str, Any]) -> dict[str, Any]:
    if str(command.get("action") or "").strip() != "list_web_event_tags":
        raise WebEventBridgeError("only action=list_web_event_tags is supported")
    account_id = str(command.get("account_id") or DEFAULT_ACCOUNT_ID).strip()
    if not account_id:
        raise WebEventBridgeError("account_id is required")
    response = requests.get(
        f"{BASE_URL}/{API_VERSION}/accounts/{account_id}/web_event_tags",
        params={"with_deleted": str(bool(command.get("with_deleted", False))).lower()},
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
    return payload


def _write_result(title: str, payload: dict[str, Any]) -> None:
    RESULT_PATH.write_text(
        f"### {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )


def main() -> int:
    try:
        command = _read_command()
        payload = _request_tags(command)
        _write_result("X Ads web event tags result", payload)
        return 0
    except Exception as exc:
        _write_result("X Ads web event tags failed", {"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
