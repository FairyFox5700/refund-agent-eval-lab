from __future__ import annotations

from dataclasses import asdict
from datetime import date
from hashlib import sha256
from typing import Any

from .data import CUSTOMERS, POLICY
from .models import Intent, Outcome, Run, Scenario, TraceEvent


def _trace(events: list[TraceEvent], kind: str, name: str, summary: str,
           inputs: dict[str, Any] | None = None, outputs: dict[str, Any] | None = None,
           citations: list[str] | None = None) -> None:
    events.append(TraceEvent(len(events) + 1, kind, name, "passed", summary,
                             inputs or {}, outputs or {}, citations or []))


def _run_id(scenario: Scenario) -> str:
    payload = f"{scenario.id}|{scenario.message}|{scenario.requested_on}|{scenario.username}|{scenario.purchase_id}|{scenario.requested_items}"
    return "run_" + sha256(payload.encode()).hexdigest()[:12]


def execute(scenario: Scenario, created_at: str) -> Run:
    events: list[TraceEvent] = []
    tools: list[str] = []
    reasons: list[str] = []
    total: int | None = None
    outcome: Outcome

    _trace(events, "rule", "validate_request", "Input schema and intent validated.",
           {"scenario_id": scenario.id, "intent": scenario.intent.value})

    if scenario.intent == Intent.INFORMATIONAL:
        outcome = Outcome.INFORMATIONAL
        response = f"Our standard refund window is {POLICY['window_days']} calendar days from purchase."
        _trace(events, "retrieval", "retrieve_policy", "Returned the versioned refund-window policy.",
               outputs={"policy_id": POLICY["id"]}, citations=["policy.window"])
    elif not scenario.username:
        outcome = Outcome.NEEDS_INFORMATION
        response = "Please provide your username so I can look up the purchase."
        _trace(events, "guardrail", "required_information", "Stopped before customer lookup: username is missing.",
               outputs={"missing": ["username"]})
    else:
        tools.append("lookup_customer")
        customer = CUSTOMERS.get(scenario.username)
        _trace(events, "tool", "lookup_customer", "Customer lookup completed.",
               {"username": scenario.username}, {"found": customer is not None})
        if customer is None:
            outcome = Outcome.CUSTOMER_NOT_FOUND
            response = "I couldn't find that customer. Please verify the username."
        else:
            tools.append("check_eligibility")
            purchase = next((p for p in customer.purchases if p.purchase_id == scenario.purchase_id), None)
            if purchase is None:
                reasons.append("purchase_not_found")
            elif date.fromisoformat(scenario.requested_on) < date.fromisoformat(purchase.purchased_on):
                reasons.append("request_before_purchase")
            elif (date.fromisoformat(scenario.requested_on) - date.fromisoformat(purchase.purchased_on)).days > POLICY["window_days"]:
                reasons.append("outside_refund_window")
            if not scenario.requested_items:
                reasons.append("empty_item_request")

            lines: list[dict[str, Any]] = []
            if purchase:
                purchase_items = {item.product_id: item for item in purchase.items}
                for requested in scenario.requested_items:
                    owned = purchase_items.get(requested.product_id)
                    if owned is None:
                        reasons.append("item_not_purchased")
                    elif requested.quantity > owned.quantity:
                        reasons.append("quantity_exceeds_purchased")
                    else:
                        lines.append({"product_id": owned.product_id, "quantity": requested.quantity,
                                      "unit_cents": owned.unit_cents,
                                      "line_cents": requested.quantity * owned.unit_cents})
            _trace(events, "rule", "check_eligibility",
                   "Eligibility rules passed." if not reasons else "Request is not eligible.",
                   {"purchase_id": scenario.purchase_id, "requested_items": [asdict(x) for x in scenario.requested_items]},
                   {"eligible": not reasons, "reasons": reasons},
                   ["policy.window", "policy.ownership", "policy.scope"])

            if reasons:
                outcome = Outcome.INELIGIBLE
                readable = reasons[0].replace("_", " ")
                response = f"I can't propose this refund because: {readable}."
            else:
                tools.append("calculate_refund")
                total = sum(line["line_cents"] for line in lines)
                _trace(events, "tool", "calculate_refund", "Calculated only explicitly requested eligible items.",
                       {"lines": lines}, {"total_cents": total, "currency": POLICY["currency"]}, ["policy.scope"])
                tools.append("simulate_ticket")
                ticket_id = "SIM-" + sha256(f"{scenario.id}|{total}".encode()).hexdigest()[:8].upper()
                _trace(events, "tool", "simulate_ticket", "Created a local ticket draft; no external action occurred.",
                       {"total_cents": total}, {"ticket_id": ticket_id, "status": "simulated"}, ["policy.review"])
                outcome = Outcome.NEEDS_HUMAN_REVIEW
                response = (f"Refund recommended for ${total / 100:.2f}. A simulated ticket ({ticket_id}) "
                            "is ready for human review; no refund has been executed.")
                _trace(events, "guardrail", "human_review_boundary", "Stopped before any external refund action.",
                       outputs={"external_action": False, "state": outcome.value}, citations=["policy.review"])

    _trace(events, "evaluation", "workflow_completed", f"Workflow ended in {outcome.value}.",
           outputs={"outcome": outcome.value, "external_refund_calls": 0})

    return Run(_run_id(scenario), scenario.id, created_at, "deterministic", "local",
               "refund-suite-v1", "pending", outcome.value, response, total, reasons, tools,
               events, [], 0.0, 12)
