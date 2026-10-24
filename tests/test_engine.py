from __future__ import annotations

import copy
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from refund_eval_lab.data import SCENARIOS, SCENARIOS_BY_ID
from refund_eval_lab.engine import execute
from refund_eval_lab.evaluator import evaluate
from refund_eval_lab.models import RequestedItem
from refund_eval_lab.service import run_suite


class EngineTests(unittest.TestCase):
    def run_case(self, scenario_id: str):
        scenario = SCENARIOS_BY_ID[scenario_id]
        return evaluate(execute(scenario, "2026-10-20T00:00:00+00:00"), scenario)

    def test_all_eight_video_scenarios_pass(self):
        report = run_suite()
        self.assertEqual(8, report["total"])
        self.assertEqual(8, report["passed"])
        self.assertEqual(0, report["failed"])

    def test_eligible_flow_stops_at_human_review(self):
        run = self.run_case("eligible_refund")
        self.assertEqual("needs_human_review", run.outcome)
        self.assertIn("no refund has been executed", run.response.lower())
        self.assertEqual("human_review_boundary", run.trace[-2].name)
        self.assertEqual(8900, run.proposed_total_cents)

    def test_specific_item_excludes_other_purchase_lines(self):
        run = self.run_case("specific_item")
        self.assertEqual(1800, run.proposed_total_cents)
        calculation = next(e for e in run.trace if e.name == "calculate_refund")
        self.assertEqual(["SKU-CABLE"], [x["product_id"] for x in calculation.input["lines"]])

    def test_prompt_injection_does_not_override_policy(self):
        run = self.run_case("item_not_purchased")
        self.assertEqual("ineligible", run.outcome)
        self.assertEqual(["item_not_purchased"], run.reasons)
        self.assertNotIn("simulate_ticket", run.tools_called)

    def test_exact_thirty_day_boundary_is_eligible(self):
        source = SCENARIOS_BY_ID["eligible_refund"]
        boundary = replace(source, requested_on="2026-10-31")
        run = evaluate(execute(boundary, "fixed"), boundary)
        self.assertEqual("needs_human_review", run.outcome)

    def test_thirty_one_days_is_ineligible(self):
        source = SCENARIOS_BY_ID["eligible_refund"]
        boundary = replace(source, requested_on="2026-11-01", expected_outcome=source.expected_outcome)
        run = execute(boundary, "fixed")
        self.assertEqual("ineligible", run.outcome)
        self.assertEqual(["outside_refund_window"], run.reasons)

    def test_quantity_cannot_exceed_purchase(self):
        source = SCENARIOS_BY_ID["specific_item"]
        invalid = replace(source, requested_items=(RequestedItem("SKU-CABLE", 3),))
        run = execute(invalid, "fixed")
        self.assertEqual(["quantity_exceeds_purchased"], run.reasons)
        self.assertIsNone(run.proposed_total_cents)

    def test_deterministic_core_ignoring_created_at(self):
        scenario = SCENARIOS[0]
        a = execute(scenario, "one").to_dict()
        b = execute(scenario, "two").to_dict()
        a.pop("created_at"); b.pop("created_at")
        self.assertEqual(a, b)

    def test_evaluator_detects_mutated_amount(self):
        scenario = SCENARIOS_BY_ID["eligible_refund"]
        run = execute(scenario, "fixed")
        run.proposed_total_cents = 999999
        evaluated = evaluate(run, scenario)
        self.assertEqual("failed", evaluated.status)
        self.assertFalse(next(m for m in evaluated.metrics if m.id == "argument_correctness").passed)


if __name__ == "__main__":
    unittest.main()
