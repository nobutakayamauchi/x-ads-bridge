from __future__ import annotations

from decimal import Decimal

import pytest

from x_signal_collector import XSignalError, collection_plan, estimate_post_read_cost_usd, search_recent_posts


def test_cost_estimate_for_default_bounded_sample():
    assert estimate_post_read_cost_usd(20) == Decimal("0.100")


def test_collection_plan_is_blocked_by_default(monkeypatch):
    monkeypatch.delenv("X_SIGNAL_ALLOW_PAID_READS", raising=False)
    monkeypatch.delenv("X_SIGNAL_MAX_COST_USD_PER_RUN", raising=False)
    plan = collection_plan("GPTs 販売 lang:ja -is:retweet", max_results=20)
    assert plan["within_cost_cap"] is True
    assert plan["paid_reads_enabled"] is False
    assert plan["estimated_max_cost_usd"] == "0.100"


def test_cost_cap_blocks_oversized_run(monkeypatch):
    monkeypatch.setenv("X_SIGNAL_ALLOW_PAID_READS", "true")
    monkeypatch.setenv("X_SIGNAL_MAX_COST_USD_PER_RUN", "0.10")
    with pytest.raises(XSignalError, match="exceeds configured cap"):
        search_recent_posts("生成AI", max_results=100)


def test_invalid_result_count_is_rejected():
    with pytest.raises(XSignalError):
        estimate_post_read_cost_usd(101)
