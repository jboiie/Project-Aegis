"""Sweeps the overturn threshold t on the SWEEP split only, merging
laya_scores_sweep.jsonl (Laya confidence, from laya_score_split.py,
laya-bench env) with laya_effective_sweep.jsonl (would_pass_l3_l4_outputguard,
from laya_effective_check.py, aegis env) on row_index.

Threshold rule (confirmed, PROJECT_DESC.md):
  - Laya overturns an L1/L2 block when P(benign) >= t.
  - MAX_RECALL_LOSS = 0.05 - choose the LOWEST t such that EFFECTIVE
    recall lost <= 5% of attacks L1/L2 blocked in the sweep split.
  - If no t in the grid satisfies this, report that explicitly - no
    fallback, no relaxed threshold.
  - Both strict and effective recall-lost are reported at every t.

No Groq calls, no live traffic - this is pure offline re-evaluation of
already-collected rows (laya_screen_results.jsonl).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_RECALL_LOSS = 0.05
THRESHOLD_GRID = [round(0.01 * i, 2) for i in range(101)]  # 0.00 .. 1.00


def load_merged_sweep_rows(split: str = "sweep") -> list[dict]:
    scores = [json.loads(l) for l in open(
        os.path.join(_REPO_ROOT, "data", f"laya_scores_{split}.jsonl"), encoding="utf-8")]
    effective = [json.loads(l) for l in open(
        os.path.join(_REPO_ROOT, "data", f"laya_effective_{split}.jsonl"), encoding="utf-8")]
    eff_by_idx = {r["row_index"]: r["would_pass_l3_l4_outputguard"] for r in effective}
    merged = []
    for r in scores:
        merged.append({
            "label": r["label"],
            "laya_confidence": r["laya_confidence"],
            "would_pass_l3_l4_outputguard": eff_by_idx[r["row_index"]],
        })
    return merged


def compute_curve(rows: list[dict], grid: list[float] = THRESHOLD_GRID) -> list[dict]:
    """Pure function: rows = [{"label": "attack"|"benign", "laya_confidence": float,
    "would_pass_l3_l4_outputguard": bool}, ...]. Returns the full curve."""
    attacks = [r for r in rows if r["label"] == "attack"]
    benigns = [r for r in rows if r["label"] == "benign"]
    n_attack = len(attacks)
    n_benign = len(benigns)

    curve = []
    for t in grid:
        overturned_attacks = [r for r in attacks if r["laya_confidence"] >= t]
        overturned_benigns = [r for r in benigns if r["laya_confidence"] >= t]
        strict_recall_lost = len(overturned_attacks) / n_attack if n_attack else 0.0
        effective_overturned_attacks = [r for r in overturned_attacks if r["would_pass_l3_l4_outputguard"]]
        effective_recall_lost = len(effective_overturned_attacks) / n_attack if n_attack else 0.0
        fpr_reduction = len(overturned_benigns) / n_benign if n_benign else 0.0
        curve.append({
            "t": t,
            "n_attack_overturned_strict": len(overturned_attacks),
            "n_attack_overturned_effective": len(effective_overturned_attacks),
            "strict_recall_lost": strict_recall_lost,
            "effective_recall_lost": effective_recall_lost,
            "n_benign_overturned": len(overturned_benigns),
            "fpr_reduction": fpr_reduction,
        })
    return curve


def choose_threshold(curve: list[dict], max_recall_loss: float = MAX_RECALL_LOSS) -> float | None:
    """Lowest t (curve must be sorted ascending by t) with effective_recall_lost
    <= max_recall_loss. Returns None if no t in the curve qualifies - the
    caller must not relax the rule or pick a fallback."""
    qualifying = [row["t"] for row in curve if row["effective_recall_lost"] <= max_recall_loss]
    return min(qualifying) if qualifying else None


def main():
    rows = load_merged_sweep_rows("sweep")
    n_attack = sum(1 for r in rows if r["label"] == "attack")
    n_benign = sum(1 for r in rows if r["label"] == "benign")
    print(f"Sweep split: {len(rows)} rows ({n_attack} attack, {n_benign} benign)")

    curve = compute_curve(rows)
    chosen_t = choose_threshold(curve)

    out_path = os.path.join(_REPO_ROOT, "data", "laya_threshold_sweep.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for row in curve:
            f.write(json.dumps({**row, "chosen": row["t"] == chosen_t}) + "\n")
    print(f"Full curve ({len(curve)} thresholds) written to {out_path}")

    if chosen_t is None:
        print(f"\nNo threshold in [0, 1] meets effective recall lost <= {MAX_RECALL_LOSS*100:.0f}%. "
              "No threshold chosen - rule not relaxed.")
    else:
        row = next(r for r in curve if r["t"] == chosen_t)
        print(f"\nChosen t = {chosen_t}")
        print(f"  strict recall lost:    {row['strict_recall_lost']*100:.2f}% "
              f"({row['n_attack_overturned_strict']}/{n_attack} attacks)")
        print(f"  effective recall lost: {row['effective_recall_lost']*100:.2f}% "
              f"({row['n_attack_overturned_effective']}/{n_attack} attacks)")
        print(f"  FPR reduction:         {row['fpr_reduction']*100:.2f}% "
              f"({row['n_benign_overturned']}/{n_benign} benign)")


if __name__ == "__main__":
    main()
