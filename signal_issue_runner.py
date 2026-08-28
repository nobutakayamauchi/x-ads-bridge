from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hypothesis_search import run_h1_search
from x_signal_collector import XSignalError


def _event_issue() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH", "").strip()
    if not event_path:
        return {}
    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    return payload.get("issue") or {}


def _post_url(source_id: str) -> str:
    return f"https://x.com/i/web/status/{source_id}" if source_id else ""


def _write_markdown(result: dict[str, Any]) -> None:
    lines = [
        "## H1 purposeful X search",
        "",
        f"**Hypothesis:** `{result['hypothesis_id']}`",
        "",
        result["statement"],
        "",
        "### Retrieval",
        "",
        f"- requested Post-read cap: **{result['requested_post_read_cap']}**",
        f"- unique Posts inspected: **{result['unique_posts']}**",
        f"- DIRECT H1 evidence: **{result['direct_h1_cases']}**",
        f"- INDIRECT H1 evidence: **{result['indirect_h1_cases']}**",
        f"- CASE_READY Posts: **{result['case_ready_posts']}**",
        f"- discarded as irrelevant to H1: **{result['irrelevant_posts']}**",
        "",
        "### Search stages",
        "",
    ]
    for stage in result.get("stages") or []:
        lines.append(f"- `{stage['name']}`: {stage['result_count']} Posts")

    lines.extend(["", "### Evidence retained", ""])
    evidence = result.get("evidence") or []
    if not evidence:
        lines.append("No DIRECT/INDIRECT H1 evidence was retained in this bounded run.")
    for index, row in enumerate(evidence, start=1):
        case = row.get("case") or {}
        triad = case.get("triad") or {}
        lines.extend([
            f"#### {index}. {row['h1_evidence_class']} / {case.get('case_class', 'UNKNOWN')}",
            "",
            f"- source: {_post_url(str(row.get('source_id') or ''))}",
            f"- conversation_id: `{row.get('conversation_id') or ''}`",
            f"- Intent/Test/Outcome: `{triad.get('intent')}/{triad.get('test')}/{triad.get('outcome')}`",
            f"- quantitative outcome: `{case.get('quantitative_outcome')}`",
            f"- metrics: `{json.dumps(case.get('metric_mentions') or [], ensure_ascii=False)}`",
            "",
            "> " + str(row.get("text") or "").replace("\n", " ")[:500],
            "",
        ])

    lines.extend([
        "### Decision boundary",
        "",
        result["decision_rule"],
        "",
        "External cases never authorize SCALE by themselves.",
    ])
    Path("result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    issue = _event_issue()
    title = str(issue.get("title") or "")
    if not title.startswith("[xsignal] H1"):
        raise SystemExit("unsupported signal issue; expected title prefix '[xsignal] H1'")

    try:
        result = run_h1_search()
    except XSignalError as exc:
        Path("result.md").write_text(
            "## H1 purposeful X search failed\n\n"
            f"`{exc}`\n\nNo evidence record was stored.\n",
            encoding="utf-8",
        )
        raise

    result["trigger_issue_number"] = issue.get("number")
    result["trigger_issue_url"] = issue.get("html_url")
    Path("result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_markdown(result)


if __name__ == "__main__":
    main()
