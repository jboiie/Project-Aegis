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


def test_compute_metrics_excludes_errored():
    # A request/API failure has no real verdict - previously this was
    # scored via `not r.bypassed` as a "correctly blocked" true positive,
    # since errored results default bypassed=False. That silently inflated
    # true_positives and deflated ASR. See PROJECT_DESC.md's
    # error-handling audit and the pair.py bug it was found from.
    results = [
        AttackResult(strategy="pair", prompt="x", response="ok", bypassed=True, confidence=1.0),
        AttackResult(strategy="pair", prompt="y", response="[ERROR] ConnectError", bypassed=False,
                     confidence=0.0, errored=True),
        AttackResult(strategy="pair", prompt="z", response="[ERROR] ConnectError", bypassed=False,
                     confidence=0.0, errored=True),
    ]
    metrics = compute_metrics(results)

    assert metrics.total == 1  # the 2 errored rows excluded, not counted as blocked
    assert metrics.true_positives == 0
    assert metrics.false_negatives == 1
    assert metrics.attack_success_rate == 1.0  # would read 0.33 if errors were miscounted as blocks


def test_labeled_metrics_excludes_errored():
    # None = errored (request failed), not False ("not blocked"). Previously
    # run_eval.py mapped a failed request to blocked=False directly, which
    # scored an errored attack row as a missed attack (FN) and an errored
    # benign row as a correctly-allowed one (TN) - see PROJECT_DESC.md.
    results = [
        ("attack", True),          # real TP
        ("attack", None),          # errored - excluded, not a real FN
        ("benign", None),          # errored - excluded, not a real TN
        ("benign", False),         # real TN
    ]
    metrics = compute_labeled_metrics(results)

    assert metrics.total == 2  # 2 errored rows excluded
    assert metrics.true_positives == 1
    assert metrics.false_negatives == 0
    assert metrics.true_negatives == 1
    assert metrics.false_positives == 0
