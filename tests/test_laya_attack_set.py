"""Tests for redteam/laya_attack_set.py's split logic - every wrapper
variant of the same AdvBench goal must land in the same split, or the
Laya experiment would calibrate/sweep on one wrapping of a goal and test
on another wrapping of the SAME goal, leaking goal-specific signal across
the split boundary."""

from redteam.laya_attack_set import _assign_split_by_key


def test_same_goal_rows_land_in_same_split():
    rows = []
    for goal in ["goal_a", "goal_b", "goal_c", "goal_d"]:
        for wrapper in range(10):  # 10 wrapper variants per goal, like the real 5 template + 5 encoding
            rows.append({"goal": goal, "wrapper": wrapper})

    _assign_split_by_key(rows, key_fn=lambda r: r["goal"])

    for goal in ["goal_a", "goal_b", "goal_c", "goal_d"]:
        splits_for_goal = {r["split"] for r in rows if r["goal"] == goal}
        assert len(splits_for_goal) == 1, f"{goal} rows landed in multiple splits: {splits_for_goal}"


def test_splits_are_disjoint_and_cover_all_rows():
    rows = [{"goal": f"goal_{i}"} for i in range(20)]
    _assign_split_by_key(rows, key_fn=lambda r: r["goal"])

    splits_seen = {r["split"] for r in rows}
    assert splits_seen <= {"calibration", "sweep", "test"}
    assert all("split" in r for r in rows)


def test_row_level_split_when_key_is_unique_per_row():
    # labeled_eval_set.jsonl rows have no shared goal - id() as the key
    # function gives each row its own group, i.e. ordinary row-level split.
    rows = [{"i": i} for i in range(25)]
    _assign_split_by_key(rows, key_fn=lambda r: id(r))

    from collections import Counter
    counts = Counter(r["split"] for r in rows)
    assert sum(counts.values()) == 25
    # Roughly 30/40/30 - not exact due to rounding, but no split empty.
    assert counts["calibration"] > 0 and counts["sweep"] > 0 and counts["test"] > 0
