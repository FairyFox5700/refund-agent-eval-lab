"""Optional live-framework seams.

The baseline project intentionally runs without network access or API keys. A live
adapter must preserve the same Run contract and may never receive an external
refund-execution capability.
"""
from __future__ import annotations


def integration_status() -> dict[str, bool]:
    status: dict[str, bool] = {}
    for package in ("langchain", "deepeval"):
        try:
            __import__(package)
            status[package] = True
        except ImportError:
            status[package] = False
    return status


def require_live_dependencies() -> None:
    status = integration_status()
    missing = [name for name, available in status.items() if not available]
    if missing:
        raise RuntimeError(
            "Optional live integration is unavailable. Install the 'live' extra: "
            + ", ".join(missing)
        )
