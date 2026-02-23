from src.evaluation.simulation import (
    run_fraud_simulation,
    run_scoring_performance_benchmark,
)


def test_fraud_simulation_meets_reduction_target() -> None:
    metrics = run_fraud_simulation(total_cases=200, seed=25205)

    assert metrics.total_cases == 200
    assert metrics.fraud_cases > 0
    assert metrics.baseline_successful_fraud >= metrics.protected_successful_fraud
    assert metrics.fraud_reduction_percent >= 20.0


def test_scoring_performance_is_low_latency() -> None:
    perf = run_scoring_performance_benchmark(iterations=250)

    assert perf.scoring_avg_ms >= 0
    assert perf.scoring_p95_ms >= 0
    assert perf.scoring_p95_ms < 10.0
