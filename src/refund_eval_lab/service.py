from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .data import POLICY, SCENARIOS, SCENARIOS_BY_ID
from .engine import execute
from .evaluator import evaluate

RUNS: dict[str, dict[str, Any]] = {}


def list_scenarios() -> list[dict[str, Any]]:
    return [{
        "id": s.id, "title": s.title, "category": s.category, "message": s.message,
        "expected_outcome": s.expected_outcome.value,
        "expected_total_cents": s.expected_total_cents,
    } for s in SCENARIOS]


def scenario_detail(scenario_id: str) -> dict[str, Any] | None:
    s = SCENARIOS_BY_ID.get(scenario_id)
    if not s:
        return None
    return {
        "id": s.id, "title": s.title, "category": s.category, "message": s.message,
        "intent": s.intent.value, "requested_on": s.requested_on, "username": s.username,
        "purchase_id": s.purchase_id,
        "requested_items": [{"product_id": i.product_id, "quantity": i.quantity} for i in s.requested_items],
        "expected": {"outcome": s.expected_outcome.value, "tools": list(s.expected_tools),
                     "total_cents": s.expected_total_cents, "reasons": list(s.expected_reasons)},
    }


def run_scenario(scenario_id: str) -> dict[str, Any]:
    scenario = SCENARIOS_BY_ID.get(scenario_id)
    if not scenario:
        raise KeyError(scenario_id)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = evaluate(execute(scenario, created_at), scenario).to_dict()
    RUNS[result["id"]] = result
    return result


def run_suite() -> dict[str, Any]:
    results = [run_scenario(s.id) for s in SCENARIOS]
    passed = sum(r["status"] == "passed" for r in results)
    return {
        "dataset_version": "refund-suite-v1", "policy_version": POLICY["id"],
        "total": len(results), "passed": passed, "failed": len(results) - passed,
        "pass_rate": passed / len(results), "results": results,
    }
