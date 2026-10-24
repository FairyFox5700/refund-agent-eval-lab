from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Intent(StrEnum):
    INFORMATIONAL = "informational"
    REFUND = "refund_request"


class Outcome(StrEnum):
    INFORMATIONAL = "informational"
    NEEDS_INFORMATION = "needs_information"
    CUSTOMER_NOT_FOUND = "customer_not_found"
    INELIGIBLE = "ineligible"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


@dataclass(frozen=True, slots=True)
class PurchaseItem:
    product_id: str
    name: str
    quantity: int
    unit_cents: int


@dataclass(frozen=True, slots=True)
class Purchase:
    purchase_id: str
    purchased_on: str
    items: tuple[PurchaseItem, ...]


@dataclass(frozen=True, slots=True)
class Customer:
    username: str
    purchases: tuple[Purchase, ...]


@dataclass(frozen=True, slots=True)
class RequestedItem:
    product_id: str
    quantity: int = 1


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    title: str
    category: str
    intent: Intent
    message: str
    requested_on: str
    username: str | None
    purchase_id: str | None
    requested_items: tuple[RequestedItem, ...]
    expected_outcome: Outcome
    expected_tools: tuple[str, ...]
    expected_total_cents: int | None = None
    expected_reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class TraceEvent:
    order: int
    type: str
    name: str
    status: str
    summary: str
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    citation_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Metric:
    id: str
    label: str
    score: float
    threshold: float
    passed: bool
    explanation: str
    evidence: list[str]
    scorer: str = "local"


@dataclass(slots=True)
class Run:
    id: str
    scenario_id: str
    created_at: str
    engine: str
    evaluator: str
    dataset_version: str
    status: str
    outcome: str
    response: str
    proposed_total_cents: int | None
    reasons: list[str]
    tools_called: list[str]
    trace: list[TraceEvent]
    metrics: list[Metric]
    composite_score: float
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
