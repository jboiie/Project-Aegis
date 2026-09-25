"""Re-fits temperature + ECE on the CLEANED calibration split, reusing
the cached raw Laya scores from data/laya_calibration_scores.jsonl
instead of re-invoking Laya. Laya's output is deterministic given text,
and no surviving row's text changed - only 1 mislabeled benign row was
removed from the calibration population. Re-running Laya on the other
1197 unchanged rows would reproduce identical s_raw values, so this
re-filters the cache and refits, which is mathematically equivalent to
a full re-run but skips ~40 minutes of redundant CPU inference.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redteam.laya_calibrate import (
    compute_ece, fit_temperature, CALIBRATION_OUT_PATH, SCREEN_RESULTS_PATH,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHED_SCORES_PATH = os.path.join(_REPO_ROOT, "data", "laya_calibration_scores.jsonl")

cached = [json.loads(l) for l in open(CACHED_SCORES_PATH, encoding="utf-8")]
print(f"cached calibration scores: {len(cached)}")

current_screen = [json.loads(l) for l in open(SCREEN_RESULTS_PATH, encoding="utf-8")]
current_calib_blocked = {
    r["prompt"] for r in current_screen
    if r["split"] == "calibration" and r["blocking_layer"] in ("L1", "L2")
}
print(f"current cleaned calibration blocked rows: {len(current_calib_blocked)}")

scored = [r for r in cached if r["prompt"] in current_calib_blocked]
dropped = [r for r in cached if r["prompt"] not in current_calib_blocked]
print(f"scored (kept): {len(scored)}  dropped: {len(dropped)}")
for r in dropped:
    print(f"  dropped row: label={r['label']} s_raw={r['s_raw']:.4f} prompt={r['prompt'][:80]!r}")

n_attack = sum(1 for r in scored if r["label"] == "attack")
n_benign = sum(1 for r in scored if r["label"] == "benign")
print(f"cleaned calibration set: {len(scored)} ({n_attack} attack, {n_benign} benign)")

ece_before = compute_ece(scored, T=1.0)
T_fitted = fit_temperature(scored)
ece_after = compute_ece(scored, T=T_fitted)

print(f"\nFitted temperature: T={T_fitted}")
print(f"ECE before (T=1.0): combined={ece_before['ece_combined']:.4f}  "
      f"attack={ece_before['ece_attack']:.4f}  benign={ece_before['ece_benign']:.4f}")
print(f"ECE after  (T={T_fitted}): combined={ece_after['ece_combined']:.4f}  "
      f"attack={ece_after['ece_attack']:.4f}  benign={ece_after['ece_benign']:.4f}")

out = {
    "temperature": T_fitted,
    "class_balance_method": "class_balanced_weighting",
    "n_calibration_rows": len(scored),
    "n_attack": n_attack,
    "n_benign": n_benign,
    "score_definition": "s = max(jailbreak.noul, prompt_injection.noul); "
                         "confidence_rank_score = 1 - sigmoid(logit(s)/T) (an empirically "
                         "ranked overturn score, NOT a calibrated probability - see PROJECT_DESC.md)",
    "ece_before": ece_before,
    "ece_after": ece_after,
    "refit_on_cleaned_data": True,
    "note": "refit after dropping 1 mislabeled benign calibration row "
            "(batches-1-2 literal_editing_instruction audit)",
}
with open(CALIBRATION_OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(f"\nWritten to {CALIBRATION_OUT_PATH}")

# save cleaned scores too, for the sweep-side recovery step
CLEANED_SCORES_PATH = os.path.join(_REPO_ROOT, "data", "laya_calibration_scores.jsonl")
with open(CLEANED_SCORES_PATH, "w", encoding="utf-8") as f:
    for r in scored:
        f.write(json.dumps(r) + "\n")
print(f"Overwrote {CLEANED_SCORES_PATH} with {len(scored)} cleaned rows")
