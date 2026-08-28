from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


class CreativeReferenceError(ValueError):
    pass


_ALLOWED_HOSTS = {
    "x.com",
    "www.x.com",
    "twitter.com",
    "www.twitter.com",
    "mobile.twitter.com",
}
_STATUS_RE = re.compile(r"/status/(\d+)(?:/|$)")


def tweet_id_from_url(value: object) -> str:
    url = str(value or "").strip()
    if not url:
        raise CreativeReferenceError("tweet URL is empty")

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in _ALLOWED_HOSTS:
        raise CreativeReferenceError("tweet URL must be an x.com or twitter.com status URL")

    match = _STATUS_RE.search(parsed.path)
    if not match:
        raise CreativeReferenceError("tweet URL does not contain /status/<tweet_id>")
    return match.group(1)


def normalize_tweet_references(proposed: dict[str, Any]) -> dict[str, Any]:
    """Return a canonical copy with tweet_url(s) converted to tweet_ids.

    The normalized object is what the approval protocol signs, so a URL cannot
    silently resolve to a different creative after approval.
    """
    out = dict(proposed)
    ids: list[str] = []

    raw_ids = out.get("tweet_ids")
    if raw_ids is not None:
        if not isinstance(raw_ids, list):
            raise CreativeReferenceError("tweet_ids must be a list")
        ids.extend(str(value).strip() for value in raw_ids if str(value).strip())

    if "tweet_url" in out:
        ids.append(tweet_id_from_url(out.get("tweet_url")))

    raw_urls = out.get("tweet_urls")
    if raw_urls is not None:
        if not isinstance(raw_urls, list):
            raise CreativeReferenceError("tweet_urls must be a list")
        ids.extend(tweet_id_from_url(value) for value in raw_urls)

    if ids:
        deduped: list[str] = []
        seen: set[str] = set()
        for tweet_id in ids:
            if tweet_id not in seen:
                seen.add(tweet_id)
                deduped.append(tweet_id)
        out["tweet_ids"] = deduped

    out.pop("tweet_url", None)
    out.pop("tweet_urls", None)
    return out


def normalize_bundle_command(command: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize creative references before proposal validation/signing."""
    out = dict(command)
    proposed = out.get("proposed_command")
    if isinstance(proposed, dict):
        out["proposed_command"] = normalize_tweet_references(proposed)
    return out
