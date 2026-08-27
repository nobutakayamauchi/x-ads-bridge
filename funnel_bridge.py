from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote

import requests


class FunnelBridgeError(RuntimeError):
    pass


def _base_url() -> str:
    value = os.getenv("FUNNEL_API_BASE_URL", "").strip().rstrip("/")
    if not value:
        raise FunnelBridgeError("FUNNEL_API_BASE_URL is not configured")
    if not value.startswith("https://"):
        raise FunnelBridgeError("FUNNEL_API_BASE_URL must use https")
    return value


def _audit_token() -> str:
    value = os.getenv("FUNNEL_AUDIT_TOKEN", "").strip()
    if not value:
        raise FunnelBridgeError("FUNNEL_AUDIT_TOKEN is not configured")
    return value


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_audit_token()}"}


def _json_response(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise FunnelBridgeError(
            f"funnel service returned non-JSON HTTP {response.status_code}"
        ) from exc
    if not response.ok:
        raise FunnelBridgeError(
            f"funnel service HTTP {response.status_code}: "
            f"{json.dumps(payload, ensure_ascii=False)[:2000]}"
        )
    if not isinstance(payload, dict):
        raise FunnelBridgeError("funnel service response must be an object")
    return payload


def _window(command: dict[str, Any]) -> tuple[str, int, int]:
    product = str(command.get("product") or "").strip()
    start_epoch = command.get("start_epoch")
    end_epoch = command.get("end_epoch")
    if not product:
        raise FunnelBridgeError("product is required")
    try:
        start_epoch = int(start_epoch)
        end_epoch = int(end_epoch)
    except (TypeError, ValueError) as exc:
        raise FunnelBridgeError("start_epoch and end_epoch must be integers") from exc
    return product, start_epoch, end_epoch


def execute(command: dict[str, Any]) -> dict[str, Any]:
    action = str(command.get("action") or "").strip()
    if not action:
        raise FunnelBridgeError("missing action")

    base = _base_url()

    if action == "funnel_health":
        return _json_response(requests.get(f"{base}/health", timeout=20))

    if action in {"funnel_summary", "funnel_join_keys"}:
        product, start_epoch, end_epoch = _window(command)
        endpoint = "/v1/summary" if action == "funnel_summary" else "/v1/join-keys"
        response = requests.get(
            f"{base}{endpoint}",
            params={
                "product": product,
                "start_epoch": start_epoch,
                "end_epoch": end_epoch,
            },
            headers=_headers(),
            timeout=30,
        )
        return _json_response(response)

    if action == "funnel_exclude_device":
        device_id = str(command.get("device_id") or "").strip()
        label = str(command.get("label") or "owner-device").strip()
        if not device_id:
            raise FunnelBridgeError("device_id is required")
        response = requests.post(
            f"{base}/v1/exclusions",
            json={"device_id": device_id, "label": label},
            headers=_headers(),
            timeout=30,
        )
        return _json_response(response)

    if action == "funnel_unexclude_device":
        device_id = str(command.get("device_id") or "").strip()
        if not device_id:
            raise FunnelBridgeError("device_id is required")
        response = requests.delete(
            f"{base}/v1/exclusions/{quote(device_id, safe='')}",
            headers=_headers(),
            timeout=30,
        )
        return _json_response(response)

    raise FunnelBridgeError(f"unsupported action: {action}")
