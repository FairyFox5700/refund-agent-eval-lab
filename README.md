# Refund Agent Eval Lab

A runnable portfolio project inspired by **“Build an AI Agent Evaluation System with DeepEval & LangChain”**. It implements the tutorial's eight refund scenarios as a deterministic, API-key-free agent workflow and evaluation dashboard.

## What it demonstrates

- Read-only customer and purchase lookup
- A strict inclusive 30-day refund policy
- Exact requested-item and quantity validation
- Deterministic refund calculations in integer cents
- Simulated ticket creation and an explicit human-review boundary
- Structured execution traces (not hidden chain-of-thought)
- Four hard-gated local metrics: policy, tools, arguments, and safety
- A responsive browser workbench with suite runs and local regression history
- Optional LangChain/DeepEval dependency seam without misrepresenting the local demo

The agent **never executes a refund**. Eligible requests end at `needs_human_review`.

## Run

Requires Python 3.11+ and no third-party packages.

```bash
python -m unittest discover -s tests -v
PYTHONPATH=src python -m refund_eval_lab.cli suite --pretty
PYTHONPATH=src python -m refund_eval_lab.cli serve
```

Open <http://127.0.0.1:8765>.

On Windows Git Bash, use the same commands. In PowerShell, replace `PYTHONPATH=src` with `$env:PYTHONPATH='src'`.

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` | Readiness and engine identity |
| `GET /api/scenarios` | Versioned scenario catalog |
| `GET /api/scenarios/{id}` | Scenario fixture and expected trajectory |
| `POST /api/evaluate` | Run one scenario: `{"scenario_id":"eligible_refund"}` |
| `POST /api/evaluate-all` | Run all eight scenarios with `{}` |
| `GET /api/runs/{run_id}` | Read back the exact in-memory run |

The local server binds to loopback, rejects unknown fields, limits request bodies to 64 KiB, emits a restrictive CSP, and enables no CORS.

## Project map

```text
src/refund_eval_lab/
  data.py                  fixed customers, policy, eight video scenarios
  engine.py                deterministic workflow and evidence trace
  evaluator.py             hard-gated evaluation metrics
  service.py               application API
  api.py                   stdlib HTTP server and dashboard hosting
  optional_integrations.py honest LangChain/DeepEval availability seam
web/                       responsive evaluation workbench
tests/                     domain, negative, determinism, and HTTP tests
```

## Optional live integration

Install the `live` extra only when you want to replace the deterministic engine or local evaluator:

```bash
python -m pip install -e ".[live]"
```

A production adapter must preserve the `Run` contract, use the coarse-grained assessment boundary, and must not expose payment or external refund tools to the model. Semantic LLM-as-judge scores may supplement but never override policy, amount, item-set, or human-review gates.

## Source inspiration

- Video: <https://www.youtube.com/watch?v=eL9BRo-eFYY>
- Tutorial concepts retained: tools, memory-ready structured workflow, expected answers/tool calls, traces, test scenarios, and data-driven evaluation.
- Deliberate improvement: the baseline is reproducible without credentials, and high-authority refund execution is outside the agent process.
