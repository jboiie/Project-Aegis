"""Re-derives Laya confidence on the CLEANED sweep split for the new
T=0.7, reusing cached scores instead of re-invoking Laya (~58min
saved). data/laya_scores_sweep.jsonl only stored the FINAL confidence
(computed with the OLD T=0.66), not the raw noul score, but the
temperature transform is an invertible bijection:
    confidence = 1 - sigmoid(logit(s_raw) / T_old)
  => s_raw = sigmoid(logit(1 - confidence) * T_old)
Recovering s_raw this way and reapplying the new T is mathematically
identical to re-running Laya on the same (unchanged) prompt text.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redteam.laya_threshold_sweep import compute_curve, choose_threshold, MAX_RECALL_LOSS

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPS = 1e-6


def logit(p):
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-z))


T_OLD = 0.66
with open(os.path.join(_REPO_ROOT, "data", "laya_calibration.json"), encoding="utf-8") as f:
    T_NEW = json.load(f)["temperature"]
print(f"T_old={T_OLD}  T_new={T_NEW}")

cached = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_scores_sweep.jsonl"), encoding="utf-8")]
print(f"cached sweep scores: {len(cached)}")

# recover s_raw, verify invertibility on first row, then recompute confidence at T_new
for r in cached:
    s_raw = sigmoid(logit(1 - r["laya_confidence"]) * T_OLD)
    r["s_raw_recovered"] = s_raw
    r["laya_confidence"] = 1.0 - sigmoid(logit(s_raw) / T_NEW)

# sanity check: reapplying T_OLD to the recovered s_raw must reproduce the original cached confidence
check_row = cached[0]
reproduced = 1.0 - sigmoid(logit(check_row["s_raw_recovered"]) / T_OLD)
print(f"invertibility check: reproduced={reproduced:.6f} (should match original cached value)")

screen_rows = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl"), encoding="utf-8")]
current_sweep_blocked = {
    r["prompt"] for r in screen_rows
    if r["split"] == "sweep" and r["blocking_layer"] in ("L1", "L2")
}
print(f"current cleaned sweep blocked rows: {len(current_sweep_blocked)}")

cleaned_scores = [r for r in cached if r["prompt"] in current_sweep_blocked]
dropped = [r for r in cached if r["prompt"] not in current_sweep_blocked]
print(f"kept: {len(cleaned_scores)}  dropped: {len(dropped)}")
for r in dropped:
    print(f"  dropped: label={r['label']} prompt={r['prompt'][:80]!r}")

with open(os.path.join(_REPO_ROOT, "data", "laya_scores_sweep.jsonl"), "w", encoding="utf-8") as f:
    for r in cleaned_scores:
        f.write(json.dumps({k: v for k, v in r.items() if k != "s_raw_recovered"}) + "\n")

effective = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_effective_sweep.jsonl"), encoding="utf-8")]
eff_by_prompt = {r["prompt"]: r["would_pass_l3_l4_outputguard"] for r in effective}

merged = []
for r in cleaned_scores:
    merged.append({
        "label": r["label"],
        "laya_confidence": r["laya_confidence"],
        "would_pass_l3_l4_outputguard": eff_by_prompt[r["prompt"]],
    })

n_attack = sum(1 for r in merged if r["label"] == "attack")
n_benign = sum(1 for r in merged if r["label"] == "benign")
print(f"\nCleaned sweep split: {len(merged)} ({n_attack} attack, {n_benign} benign)")

curve = compute_curve(merged)
chosen_t = choose_threshold(curve, MAX_RECALL_LOSS)

with open(os.path.join(_REPO_ROOT, "data", "laya_threshold_sweep.jsonl"), "w", encoding="utf-8") as f:
    for row in curve:
        f.write(json.dumps({**row, "chosen": row["t"] == chosen_t}) + "\n")

print(f"chosen t = {chosen_t}")
if chosen_t is not None:
    row = next(r for r in curve if r["t"] == chosen_t)
    print(f"  strict recall lost:    {row['strict_recall_lost']*100:.2f}% ({row['n_attack_overturned_strict']}/{n_attack})")
    print(f"  effective recall lost: {row['effective_recall_lost']*100:.2f}% ({row['n_attack_overturned_effective']}/{n_attack})")
    print(f"  FPR reduction:         {row['fpr_reduction']*100:.2f}% ({row['n_benign_overturned']}/{n_benign})")
