"""Baseline for comparison against Laya: instead of a second-stage
model, simply raise L2's own decision threshold (currently 0.85, see
GUARDRAIL_INJECTION_THRESHOLD). Same rule as the Laya threshold: choose
on the SWEEP split (most permissive tau with effective recall lost <=
MAX_RECALL_LOSS), apply once on TEST, fixed, not re-tuned.

Raising L2's threshold can only ever un-block rows currently
blocked_by=L2 (a stricter classifier decision blocks a subset of what
a looser one blocks) - so scripts/_score_l2_confidence.py only needed
to score those rows, not re-screen the full attack/benign sets.

Direction note: Laya's rule picks the LOWEST t meeting the recall bound
(t=0 is most permissive there). Here, raising tau is what's permissive
(tau=0.85 is the unmodified baseline, tau=1.0 would un-block
everything), so this picks the HIGHEST tau meeting the bound - the
same idea (most aggressive setting within the recall budget), applied
in the direction that matches how this particular knob works.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_RECALL_LOSS = 0.05
BASE_THRESHOLD = 0.85
TAU_GRID = [round(BASE_THRESHOLD + 0.005 * i, 3) for i in range(1, int((1.0 - BASE_THRESHOLD) / 0.005) + 1)]


def load_l2_scores(split: str) -> list[dict]:
    rows = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "l2_confidence_scores.jsonl"), encoding="utf-8")]
    return [r for r in rows if r["split"] == split]


def load_effective(split: str) -> dict:
    rows = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", f"laya_effective_{split}.jsonl"), encoding="utf-8")]
    return {r["prompt"]: r["would_pass_l3_l4_outputguard"] for r in rows}


def load_total_blocked(split: str) -> tuple[int, int]:
    """Total attacks/benign blocked by L1/L2 on this split (same
    denominator convention laya_threshold_sweep.py uses)."""
    rows = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl"), encoding="utf-8")]
    blocked = [r for r in rows if r["split"] == split and r["blocking_layer"] in ("L1", "L2")]
    n_attack = sum(1 for r in blocked if r["label"] == "attack")
    n_benign = sum(1 for r in blocked if r["label"] == "benign")
    return n_attack, n_benign


def compute_curve(l2_rows: list[dict], eff_by_prompt: dict, n_attack_total: int, n_benign_total: int) -> list[dict]:
    curve = []
    for tau in TAU_GRID:
        unblocked = [r for r in l2_rows if r["l2_confidence"] < tau]
        unblocked_attacks = [r for r in unblocked if r["label"] == "attack"]
        unblocked_benign = [r for r in unblocked if r["label"] == "benign"]
        effective_attacks = [r for r in unblocked_attacks if eff_by_prompt.get(r["prompt"], False)]
        curve.append({
            "tau": tau,
            "n_attack_unblocked_strict": len(unblocked_attacks),
            "n_attack_unblocked_effective": len(effective_attacks),
            "strict_recall_lost": len(unblocked_attacks) / n_attack_total if n_attack_total else 0.0,
            "effective_recall_lost": len(effective_attacks) / n_attack_total if n_attack_total else 0.0,
            "n_benign_unblocked": len(unblocked_benign),
            "fpr_reduction": len(unblocked_benign) / n_benign_total if n_benign_total else 0.0,
        })
    return curve


def choose_tau(curve: list[dict], max_recall_loss: float = MAX_RECALL_LOSS) -> float | None:
    qualifying = [row["tau"] for row in curve if row["effective_recall_lost"] <= max_recall_loss]
    return max(qualifying) if qualifying else None


def main():
    sweep_rows = load_l2_scores("sweep")
    sweep_eff = load_effective("sweep")
    n_attack_sweep, n_benign_sweep = load_total_blocked("sweep")
    print(f"Sweep: {len(sweep_rows)} L2-blocked rows scored "
          f"(denominators: {n_attack_sweep} attacks, {n_benign_sweep} benign blocked total)")

    curve = compute_curve(sweep_rows, sweep_eff, n_attack_sweep, n_benign_sweep)
    with open(os.path.join(_REPO_ROOT, "data", "l2_threshold_sweep.jsonl"), "w", encoding="utf-8") as f:
        for row in curve:
            f.write(json.dumps(row) + "\n")

    chosen_tau = choose_tau(curve)
    print(f"Chosen tau: {chosen_tau}")
    if chosen_tau is None:
        print("No tau meets the 5% effective-recall-loss bound. L2-tuning baseline: NO VIABLE OPERATING POINT.")
        return
    row = next(r for r in curve if r["tau"] == chosen_tau)
    print(f"  strict recall lost:    {row['strict_recall_lost']*100:.2f}% ({row['n_attack_unblocked_strict']}/{n_attack_sweep})")
    print(f"  effective recall lost: {row['effective_recall_lost']*100:.2f}% ({row['n_attack_unblocked_effective']}/{n_attack_sweep})")
    print(f"  FPR reduction (sweep): {row['fpr_reduction']*100:.2f}% ({row['n_benign_unblocked']}/{n_benign_sweep})")

    with open(os.path.join(_REPO_ROOT, "data", "l2_threshold_chosen.json"), "w", encoding="utf-8") as f:
        json.dump({"tau": chosen_tau, "base_threshold": BASE_THRESHOLD}, f, indent=2)

    # ---- apply once on test, fixed ----
    print("\n--- TEST (tau fixed, applied once) ---")
    test_rows = load_l2_scores("test")
    test_eff = load_effective("test")
    n_attack_test, n_benign_test = load_total_blocked("test")

    unblocked_test = [r for r in test_rows if r["l2_confidence"] < chosen_tau]
    unblocked_attacks = [r for r in unblocked_test if r["label"] == "attack"]
    effective_attacks = [r for r in unblocked_attacks if test_eff.get(r["prompt"], False)]
    print(f"Attacks L1/L2 blocked (test): {n_attack_test}")
    print(f"  strict recall lost:    {len(unblocked_attacks)}/{n_attack_test} = {len(unblocked_attacks)/n_attack_test*100:.2f}%")
    print(f"  effective recall lost: {len(effective_attacks)}/{n_attack_test} = {len(effective_attacks)/n_attack_test*100:.2f}%")

    screen = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl"), encoding="utf-8")]
    test_benign = [r for r in screen if r["row_type"] == "benign" and r["split"] == "test"]
    unblocked_prompts = {r["prompt"] for r in unblocked_test if r["label"] == "benign"}

    def group_report(rows, label):
        n = len(rows)
        blocked = [r for r in rows if r["blocking_layer"] in ("L1", "L2")]
        n_blocked = len(blocked)
        n_unblocked = sum(1 for r in blocked if r["prompt"] in unblocked_prompts)
        n_after = n_blocked - n_unblocked
        print(f"\n  {label} (n={n}): FPR before {n_blocked}/{n} = {n_blocked/n*100:.1f}%  "
              f"L2-tuning unblocks {n_unblocked}/{n_blocked}  FPR after {n_after}/{n} = {n_after/n*100:.1f}%")

    sec_ed_b12 = [r for r in test_benign if r["category"] == "security_education" and r.get("batch") in (1, 2)]
    sec_ed_b3 = [r for r in test_benign if r["category"] == "security_education" and r.get("batch") == 3]
    group_report(sec_ed_b12, "security_education, batches 1-2")
    group_report(sec_ed_b3, "security_education, batch 3")
    group_report(sec_ed_b12 + sec_ed_b3, "security_education, COMBINED")


if __name__ == "__main__":
    main()
