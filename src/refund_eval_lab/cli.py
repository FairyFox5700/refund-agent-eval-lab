from __future__ import annotations

import argparse
import json

from .api import serve
from .service import run_scenario, run_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Refund Agent Eval Lab")
    sub = parser.add_subparsers(dest="command")
    suite = sub.add_parser("suite", help="Run all deterministic evaluation scenarios")
    suite.add_argument("--pretty", action="store_true")
    one = sub.add_parser("run", help="Run one scenario")
    one.add_argument("scenario_id")
    server = sub.add_parser("serve", help="Start the local dashboard")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.command == "serve":
        serve(args.host, args.port)
    elif args.command == "run":
        print(json.dumps(run_scenario(args.scenario_id), indent=2))
    else:
        report = run_suite()
        print(json.dumps(report, indent=2 if getattr(args, "pretty", False) else None))
        raise SystemExit(0 if report["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
