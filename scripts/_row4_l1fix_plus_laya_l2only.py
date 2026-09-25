import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redteam.laya_threshold_sweep import compute_curve, choose_threshold, MAX_RECALL_LOSS

_REPO_ROOT = "."


def load_l2_only(split):
    scores = [json.loads(l) for l in open(f"data/laya_scores_{split}.jsonl", encoding="utf-8")]
    eff = {r["prompt"]: r["would_pass_l3_l4_outputguard"] for r in
           [json.loads(l) for l in open(f"data/laya_effective_{split}.jsonl", encoding="utf-8")]}
    l2_rows = [r for r in scores if r["blocking_layer"] == "L2"]
    merged = [{"label": r["label"], "laya_confidence": r["laya_confidence"],
               "would_pass_l3_l4_outputguard": eff[r["prompt"]], "prompt": r["prompt"]}
              for r in l2_rows]
    return merged


sweep_l2 = load_l2_only("sweep")
n_attack_sweep = sum(1 for r in sweep_l2 if r["label"] == "attack")
n_benign_sweep = sum(1 for r in sweep_l2 if r["label"] == "benign")
print(f"sweep L2-only population: {len(sweep_l2)} ({n_attack_sweep} attack, {n_benign_sweep} benign)")

# Denominator note: use the FULL L1/L2-blocked-attack count (1583 sweep,
# 1193 test), matching every other row in the side-by-side table, not
# just the L2-only subset - keeps "recall lost" meaning the same
# opportunity-cost quantity across all 5 rows.
N_ATTACK_SWEEP_TOTAL = 1583
N_ATTACK_TEST_TOTAL = 1193

curve = compute_curve(sweep_l2, )
for row in curve:
    row["strict_recall_lost"] = row["n_attack_overturned_strict"] / N_ATTACK_SWEEP_TOTAL
    row["effective_recall_lost"] = row["n_attack_overturned_effective"] / N_ATTACK_SWEEP_TOTAL
t_prime = choose_threshold(curve, MAX_RECALL_LOSS)
print(f"chosen t' (Laya on L2-only, sweep, denominator={N_ATTACK_SWEEP_TOTAL}): {t_prime}")
row = next(r for r in curve if r["t"] == t_prime)
print(f"  strict/effective recall lost: {row['strict_recall_lost']*100:.2f}% / {row['effective_recall_lost']*100:.2f}%")
print(f"  benign overturned: {row['n_benign_overturned']}/{n_benign_sweep}")

test_l2 = load_l2_only("test")
n_attack_test = sum(1 for r in test_l2 if r["label"] == "attack")
overturned_test_attacks = [r for r in test_l2 if r["label"] == "attack" and r["laya_confidence"] >= t_prime]
effective_overturned = [r for r in overturned_test_attacks if r["would_pass_l3_l4_outputguard"]]
print(f"\ntest: L2-only attacks blocked = {n_attack_test} (of {N_ATTACK_TEST_TOTAL} total blocked)")
print(f"  strict recall lost: {len(overturned_test_attacks)}/{N_ATTACK_TEST_TOTAL} = {len(overturned_test_attacks)/N_ATTACK_TEST_TOTAL*100:.2f}%")
print(f"  effective recall lost: {len(effective_overturned)}/{N_ATTACK_TEST_TOTAL} = {len(effective_overturned)/N_ATTACK_TEST_TOTAL*100:.2f}%")

overturned_benign_prompts = {r["prompt"] for r in test_l2 if r["label"] == "benign" and r["laya_confidence"] >= t_prime}
print(f"  benign L2-blocked overturned: {len(overturned_benign_prompts)}/{n_attack_test if False else sum(1 for r in test_l2 if r['label']=='benign')}")

# also apply L1 fix unblocked prompts
l1fix = json.load(open("data/l1_keyword_fix_test.json", encoding="utf-8"))
l1_unblocked_prompts = set(l1fix["unblocked_prompts"])

screen = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
test_benign = [r for r in screen if r["row_type"] == "benign" and r["split"] == "test"]


def group_report(rows, label):
    n = len(rows)
    blocked = [r for r in rows if r["blocking_layer"] in ("L1", "L2")]
    n_blocked = len(blocked)
    n_after = 0
    for r in blocked:
        p = r["prompt"]
        still_blocked = True
        if p in l1_unblocked_prompts:
            still_blocked = False
        elif p in overturned_benign_prompts:
            still_blocked = False
        if still_blocked:
            n_after += 1
    print(f"  {label} (n={n}): FPR before {n_blocked}/{n}={n_blocked/n*100:.1f}%  FPR after (L1 fix + Laya-L2-only) {n_after}/{n}={n_after/n*100:.1f}%")


sec_ed_b12 = [r for r in test_benign if r["category"] == "security_education" and r.get("batch") in (1, 2)]
sec_ed_b3 = [r for r in test_benign if r["category"] == "security_education" and r.get("batch") == 3]
group_report(sec_ed_b12, "security_education b1-2")
group_report(sec_ed_b3, "security_education b3")
group_report(sec_ed_b12 + sec_ed_b3, "security_education combined")

with open("data/row4_chosen_t.json", "w", encoding="utf-8") as f:
    json.dump({"t_prime": t_prime}, f)
