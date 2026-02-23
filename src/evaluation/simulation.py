"""Deterministic simulation and performance helpers for Step 8 evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random
from statistics import mean
from time import perf_counter

from src.fraud.engine import score_transaction


@dataclass(frozen=True)
class FraudCase:
    amount: float
    recipient: str
    timestamp: str
    recent_failed_attempts: int
    is_fraud: bool


@dataclass(frozen=True)
class SimulationMetrics:
    total_cases: int
    fraud_cases: int
    baseline_successful_fraud: int
    protected_successful_fraud: int
    fraud_reduction_percent: float
    true_positive_rate_percent: float
    false_positive_rate_percent: float


@dataclass(frozen=True)
class PerformanceMetrics:
    scoring_avg_ms: float
    scoring_p95_ms: float


def run_fraud_simulation(total_cases: int = 200, seed: int = 25205) -> SimulationMetrics:
    """Compare baseline vs framework on synthetic rural-banking-like cases."""
    rng = Random(seed)
    history = _history_template()

    fraud_cases = 0
    baseline_successful_fraud = 0
    protected_successful_fraud = 0
    detected_fraud = 0
    false_positive = 0
    non_fraud_cases = 0

    for index in range(total_cases):
        case = _generate_case(rng, index)
        risk = score_transaction(
            transaction={
                "amount": case.amount,
                "recipient": case.recipient,
                "timestamp": case.timestamp,
            },
            history=history,
            recent_failed_attempts=case.recent_failed_attempts,
        )

        blocked = _is_blocked(risk["risk_level"], risk["risk_score"])

        if case.is_fraud:
            fraud_cases += 1
            baseline_successful_fraud += 1
            if blocked:
                detected_fraud += 1
            else:
                protected_successful_fraud += 1
        else:
            non_fraud_cases += 1
            if blocked:
                false_positive += 1

    reduction = 0.0
    if baseline_successful_fraud > 0:
        reduction = (
            (baseline_successful_fraud - protected_successful_fraud)
            / baseline_successful_fraud
            * 100
        )

    true_positive_rate = (detected_fraud / fraud_cases * 100) if fraud_cases else 0.0
    false_positive_rate = (false_positive / non_fraud_cases * 100) if non_fraud_cases else 0.0

    return SimulationMetrics(
        total_cases=total_cases,
        fraud_cases=fraud_cases,
        baseline_successful_fraud=baseline_successful_fraud,
        protected_successful_fraud=protected_successful_fraud,
        fraud_reduction_percent=round(reduction, 2),
        true_positive_rate_percent=round(true_positive_rate, 2),
        false_positive_rate_percent=round(false_positive_rate, 2),
    )


def run_scoring_performance_benchmark(iterations: int = 400) -> PerformanceMetrics:
    """Measure local fraud scoring runtime to check low-resource feasibility."""
    history = _history_template()
    timings_ms: list[float] = []
    base_time = datetime(2026, 2, 23, 12, 0, tzinfo=UTC)

    for i in range(iterations):
        tx = {
            "amount": 500 + (i % 7) * 100,
            "recipient": "Known Person" if i % 3 else "New Recipient",
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
        }
        start = perf_counter()
        _ = score_transaction(tx, history, recent_failed_attempts=i % 4)
        end = perf_counter()
        timings_ms.append((end - start) * 1000)

    sorted_times = sorted(timings_ms)
    p95_index = max(int(len(sorted_times) * 0.95) - 1, 0)
    return PerformanceMetrics(
        scoring_avg_ms=round(mean(timings_ms), 4),
        scoring_p95_ms=round(sorted_times[p95_index], 4),
    )


def _generate_case(rng: Random, index: int) -> FraudCase:
    base_time = datetime(2026, 2, 23, 12, 0, tzinfo=UTC)
    is_fraud = rng.random() < 0.35

    if is_fraud:
        obvious_pattern = rng.random() < 0.7
        if obvious_pattern:
            amount = rng.choice([3200.0, 4500.0, 5200.0, 8000.0])
            recipient = rng.choice(["Unknown Receiver", "Temp Account", "Unverified Person"])
            hour = rng.choice([23, 0, 1, 2, 5])
            failed_attempts = rng.choice([2, 3, 4, 5])
        else:
            # Evasive fraud profile: mimics normal behavior to reduce obvious trigger overlap.
            amount = rng.choice([1650.0, 2200.0, 2600.0, 2800.0])
            recipient = rng.choice(["Known Person", "Family Member", "Unknown Receiver"])
            hour = rng.choice([9, 11, 14, 17, 20])
            failed_attempts = rng.choice([0, 1, 2])
    else:
        amount = rng.choice([150.0, 220.0, 499.0, 780.0, 1200.0, 3050.0])
        recipient = rng.choice(["Known Person", "Family Member", "Local Merchant", "New Shop"])
        hour = rng.choice([8, 9, 10, 12, 14, 16, 19, 22])
        failed_attempts = rng.choice([0, 0, 1])

    timestamp = base_time.replace(hour=hour, minute=index % 60).isoformat()
    return FraudCase(
        amount=amount,
        recipient=recipient,
        timestamp=timestamp,
        recent_failed_attempts=failed_attempts,
        is_fraud=is_fraud,
    )


def _history_template() -> list[dict]:
    anchor = datetime(2026, 2, 23, 11, 0, tzinfo=UTC)
    return [
        {
            "amount": "250.00",
            "recipient": "Known Person",
            "timestamp": (anchor - timedelta(minutes=40)).isoformat(),
        },
        {
            "amount": "480.00",
            "recipient": "Family Member",
            "timestamp": (anchor - timedelta(minutes=22)).isoformat(),
        },
        {
            "amount": "199.00",
            "recipient": "Local Merchant",
            "timestamp": (anchor - timedelta(minutes=15)).isoformat(),
        },
    ]


def _is_blocked(risk_level: str, risk_score: int) -> bool:
    if risk_level == "HIGH":
        return True
    if risk_level == "MEDIUM" and risk_score >= 50:
        return True
    return False
