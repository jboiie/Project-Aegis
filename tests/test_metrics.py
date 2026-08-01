"""Tests for evaluation metrics computation — pure math, no network."""

from redteam.evaluation.metrics import compute_labeled_metrics, compute_metrics
from redteam.attacks.base import AttackResult


def test_labeled_metrics_perfect_classifier():
    results = [("attack", True), ("attack", True), ("benign", False), ("benign", False)]
    metrics = compute_labeled_metrics(results)

    assert metrics.true_positives == 2
    assert metrics.false_positives == 0
    assert metrics.true_negatives == 2
    assert metrics.false_negatives == 0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0
    assert metrics.attack_success_rate == 0.0


def test_labeled_metrics_with_errors():
    # 1 attack missed (FN), 1 benign wrongly blocked (FP)
    results = [
        ("attack", True), ("attack", False),
        ("benign", False), ("benign", True),
    ]
    metrics = compute_labeled_metrics(results)

    assert metrics.true_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.true_negatives == 1
    assert metrics.false_positives == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5


def test_labeled_metrics_empty():
    metrics = compute_labeled_metrics([])

    assert metrics.total == 0
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0


def test_compute_metrics_attack_only_asr():
    results = [
        AttackResult(strategy="template", prompt="x", response="[BLOCKED]", bypassed=False, confidence=1.0),
        AttackResult(strategy="template", prompt="y", response="ok", bypassed=True, confidence=1.0),
    ]
    metrics = compute_metrics(results)

    assert metrics.true_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.attack_success_rate == 0.5
