from __future__ import annotations

import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from refund_eval_lab.api import make_server


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def request(self, path: str, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(self.base + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_health(self):
        status, body = self.request("/health")
        self.assertEqual(200, status)
        self.assertEqual("ok", body["status"])

    def test_scenarios_have_unique_ids(self):
        status, body = self.request("/api/scenarios")
        ids = [s["id"] for s in body["scenarios"]]
        self.assertEqual(200, status)
        self.assertEqual(8, len(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_evaluate_and_read_back_exact_run(self):
        status, run = self.request("/api/evaluate", {"scenario_id": "eligible_refund"})
        self.assertEqual(200, status)
        status, stored = self.request("/api/runs/" + run["id"])
        self.assertEqual(200, status)
        self.assertEqual(run, stored)

    def test_unknown_scenario_is_404(self):
        status, body = self.request("/api/evaluate", {"scenario_id": "missing"})
        self.assertEqual(404, status)
        self.assertEqual("scenario_not_found", body["error"]["code"])

    def test_unknown_fields_are_rejected(self):
        status, body = self.request("/api/evaluate", {"scenario_id": "eligible_refund", "admin": True})
        self.assertEqual(400, status)
        self.assertEqual("unknown_fields", body["error"]["code"])

    def test_dashboard_is_served(self):
        with urlopen(self.base + "/", timeout=3) as response:
            text = response.read().decode()
        self.assertIn("Refund Agent Eval Lab", text)
        self.assertIn("content-security-policy", {k.lower(): v for k, v in response.headers.items()})


if __name__ == "__main__":
    unittest.main()
