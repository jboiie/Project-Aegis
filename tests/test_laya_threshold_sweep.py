import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redteam.laya_threshold_sweep import compute_curve, choose_threshold


def test_lowest_t_meeting_effective_recall_constraint_is_chosen():
    # 20 attacks: 18 "free" attacks (would_pass=False, confidence=0.2) whose
    # overturn costs nothing effective-wise, plus 2 real attacks that WOULD
    # reach the user if overturned (would_pass=True), at confidence 0.7 and
    # 0.3. At t=0.0 both real attacks are overturned -> effective loss
    # 2/20=10% (fails). At t=0.35 only the 0.7-confidence one clears ->
    # 1/20=5% (passes, exactly at the bound). t=0.75 overturns nothing.
    rows = [{"label": "attack", "laya_confidence": 0.2, "would_pass_l3_l4_outputguard": False}
            for _ in range(18)]
    rows.append({"label": "attack", "laya_confidence": 0.7, "would_pass_l3_l4_outputguard": True})
    rows.append({"label": "attack", "laya_confidence": 0.3, "would_pass_l3_l4_outputguard": True})

    grid = [0.0, 0.35, 0.75]
    curve = compute_curve(rows, grid=grid)
    chosen = choose_threshold(curve, max_recall_loss=0.05)
    assert chosen == 0.35


def test_no_threshold_meets_constraint_returns_none():
    # Every attack has confidence 1.0 and would pass L3/L4/OutputGuard -
    # overturning at any t>=0 loses 100% effective recall on this tiny set.
    rows = [{"label": "attack", "laya_confidence": 1.0, "would_pass_l3_l4_outputguard": True}
            for _ in range(5)]
    curve = compute_curve(rows, grid=[0.0, 0.5, 1.0])
    assert choose_threshold(curve, max_recall_loss=0.05) is None


def test_effective_recall_lost_never_exceeds_strict():
    rows = [
        {"label": "attack", "laya_confidence": 0.9, "would_pass_l3_l4_outputguard": True},
        {"label": "attack", "laya_confidence": 0.9, "would_pass_l3_l4_outputguard": False},
        {"label": "attack", "laya_confidence": 0.1, "would_pass_l3_l4_outputguard": True},
    ]
    curve = compute_curve(rows, grid=[0.0, 0.5, 0.95])
    for row in curve:
        assert row["effective_recall_lost"] <= row["strict_recall_lost"]


def test_benign_overturn_rate_computed_independently_of_attacks():
    rows = [
        {"label": "attack", "laya_confidence": 0.0, "would_pass_l3_l4_outputguard": False},
        {"label": "benign", "laya_confidence": 0.9, "would_pass_l3_l4_outputguard": True},
        {"label": "benign", "laya_confidence": 0.1, "would_pass_l3_l4_outputguard": True},
    ]
    curve = compute_curve(rows, grid=[0.5])
    assert curve[0]["n_benign_overturned"] == 1
    assert curve[0]["fpr_reduction"] == 0.5
