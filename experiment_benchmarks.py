from __future__ import annotations

from typing import Any


DEFAULT_WEB_TRAFFIC_BENCHMARKS = {
    "click_to_lpv_floor_pct": 80.0,
    "click_to_lpv_near_case_reference_pct": 94.14,
    "near_case_cpc_jpy": 9.16,
    "near_case_cpm_jpy": 56.8,
    "near_case_lp_to_intermediate_cvr_pct": 2.67,
}


def _ratio_pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def evaluate_webai_lpv_run(
    observed: dict[str, Any],
    *,
    control: dict[str, Any] | None = None,
    benchmarks: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate one WebAI Bridge LPV experiment without turning external benchmarks into authority.

    External benchmarks are directional references. The experiment itself is judged from
    its own X/LP/conversion evidence and the one-variable hypothesis contract.
    """
    b = {**DEFAULT_WEB_TRAFFIC_BENCHMARKS, **(benchmarks or {})}
    clicks = float(observed.get("link_clicks", 0) or 0)
    lpv = float(observed.get("landing_page_views", observed.get("lp_unique", 0)) or 0)
    spend = float(observed.get("spend_jpy", 0) or 0)
    impressions = float(observed.get("impressions", 0) or 0)
    consult = float(observed.get("consult_clicks", observed.get("consult_click_unique", 0)) or 0)

    click_to_lpv = _ratio_pct(lpv, clicks)
    consult_per_lpv = _ratio_pct(consult, lpv)
    cpc = round(spend / clicks, 2) if clicks > 0 else None
    cost_per_lpv = round(spend / lpv, 2) if lpv > 0 else None
    cpm = round((spend / impressions) * 1000.0, 2) if impressions > 0 else None

    observations: list[dict[str, Any]] = []
    if click_to_lpv is None:
        observations.append({
            "dimension": "click_to_lpv",
            "state": "UNMEASURED",
            "reason": "No measurable link-click to landing-page-view ratio yet.",
        })
    elif click_to_lpv >= b["click_to_lpv_near_case_reference_pct"]:
        observations.append({
            "dimension": "click_to_lpv",
            "state": "VERY_STRONG",
            "reason": "At or above the recent independent near-case reference.",
        })
    elif click_to_lpv >= b["click_to_lpv_floor_pct"]:
        observations.append({
            "dimension": "click_to_lpv",
            "state": "PASS",
            "reason": "Above the configured directional LP arrival floor.",
        })
    else:
        observations.append({
            "dimension": "click_to_lpv",
            "state": "DIAGNOSE",
            "reason": "A large share of link clicks are not becoming measured LP arrivals.",
        })

    if consult_per_lpv is not None:
        reference = b["near_case_lp_to_intermediate_cvr_pct"]
        observations.append({
            "dimension": "lp_to_consult",
            "state": "ABOVE_REFERENCE" if consult_per_lpv >= reference else "BELOW_REFERENCE",
            "reason": "Compared only as a directional intermediate-conversion reference; offer types differ.",
        })

    cost_context = {
        "cpc_vs_recent_near_case_multiple": round(cpc / b["near_case_cpc_jpy"], 2) if cpc is not None else None,
        "cpm_vs_recent_near_case_multiple": round(cpm / b["near_case_cpm_jpy"], 2) if cpm is not None else None,
        "warning": "CPC/CPM are not pass/fail gates because auction, targeting, creative and organic amplification differ across cases.",
    }

    control_comparison: dict[str, Any] | None = None
    if control:
        control_cpc = control.get("cpc_jpy")
        control_cpm = control.get("cpm_jpy")
        control_comparison = {
            "cpc_change_pct": round(((cpc - float(control_cpc)) / float(control_cpc)) * 100.0, 2)
            if cpc is not None and control_cpc not in (None, 0)
            else None,
            "cpm_change_pct": round(((cpm - float(control_cpm)) / float(control_cpm)) * 100.0, 2)
            if cpm is not None and control_cpm not in (None, 0)
            else None,
            "control_had_lpv_measurement": control.get("click_to_lpv_pct") is not None,
            "note": "The old WebAI control had no verified LPV event, so H1 cannot be resolved from historical LPV data alone.",
        }

    if click_to_lpv is None or lpv < 20:
        hypothesis_state = "INSUFFICIENT_SAMPLE"
    elif click_to_lpv < b["click_to_lpv_floor_pct"]:
        hypothesis_state = "LPV_SIGNAL_WORKS_BUT_FUNNEL_GAP_REMAINS"
    else:
        hypothesis_state = "LPV_SIGNAL_HEALTHY_PROCEED_TO_DOWNSTREAM_EVALUATION"

    return {
        "metrics": {
            "spend_jpy": spend,
            "impressions": impressions,
            "link_clicks": clicks,
            "landing_page_views": lpv,
            "click_to_lpv_pct": click_to_lpv,
            "cpc_jpy": cpc,
            "cpm_jpy": cpm,
            "cost_per_lpv_jpy": cost_per_lpv,
            "consult_clicks": consult,
            "consult_per_lpv_pct": consult_per_lpv,
        },
        "benchmark_context": b,
        "observations": observations,
        "cost_context": cost_context,
        "control_comparison": control_comparison,
        "hypothesis_state": hypothesis_state,
        "scale_authority": False,
        "invariant": "External benchmarks guide diagnosis only; own authoritative conversions and objective audit decide business success and SCALE.",
    }
