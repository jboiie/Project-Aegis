"""Temperature refit for Laya's jailbreak/prompt_injection noul scores,
fit on the calibration split ONLY.

Score definition (P(benign)): Laya's guard_questions() returns, per
input, `jailbreak.noul` (P(text tries to make the model ignore its
rules)) and `prompt_injection.noul` (P(text is an instruction aimed at
the system rather than a genuine user request)). Both are the relevant
signals for an L1/L2 (regex + injection-classifier) overturn decision -
L3 (toxicity) and L4 (PII) are separate concerns, not what got these
rows blocked. Combine as:

    s = max(jailbreak.noul, prompt_injection.noul)   # P(not benign)
    P(benign) = 1 - s

s is treated as "P(attack)" for calibration purposes (ground truth
y=1 for attack rows, y=0 for benign rows in the calibration split).

Class balance: the calibration split has 1191 attacks vs 8 benign rows
(the population is whatever L1/L2 actually blocks, and the guardrail
stack blocks far more real attacks than benign false positives - see
PROJECT_DESC.md's blocked-count table). Subsampling attacks down to 8
would leave a 16-row calibration set, too small to fit a stable
temperature. CHOSEN: class-balanced weighting - each row's contribution
to the fit is weighted by 0.5/n_class so both classes contribute equally
to the loss despite the 1191:8 imbalance, while still using the full
attack sample for a stable fit.

Temperature scaling: s is treated as a probability, converted to a
logit, rescaled by 1/T, then passed back through sigmoid:
    s_calibrated = sigmoid(logit(s) / T)
T is grid-searched to minimize class-balanced NLL on the calibration
split. ECE is reported before (T=1, Laya's own shipped calibration) and
after, using standard 10-bin ECE on the combined set, plus the
per-class breakdown the same bins imply (see compute_ece below).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN_RESULTS_PATH = os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl")
SCORES_OUT_PATH = os.path.join(_REPO_ROOT, "data", "laya_calibration_scores.jsonl")
CALIBRATION_OUT_PATH = os.path.join(_REPO_ROOT, "data", "laya_calibration.json")

N_BINS = 10
TEMPERATURE_GRID = [round(0.3 + 0.02 * i, 2) for i in range(int((3.0 - 0.3) / 0.02) + 1)]
EPS = 1e-6


def load_calibration_rows() -> list[dict]:
    rows = [json.loads(l) for l in open(SCREEN_RESULTS_PATH, encoding="utf-8")]
    return [r for r in rows if r["split"] == "calibration" and r["blocking_layer"] in ("L1", "L2")]


def score_rows_with_laya(rows: list[dict]) -> list[dict]:
    """Runs Laya's jailbreak + prompt_injection questions over every row.
    Requires the laya-bench conda env (laya isn't installed in aegis/argus).
    Saves raw per-row scores so this expensive pass (~2s/row on CPU) is
    never repeated."""
    import laya

    agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions", device="cpu")
    gq_full = laya.guard_questions()
    gq = {k: gq_full[k] for k in ("jailbreak", "prompt_injection")}

    scored = []
    for i, row in enumerate(rows, 1):
        result = agent.predict({"text": row["prompt"]}, gq)
        jailbreak_noul = result["answers"]["jailbreak"]["noul"]
        injection_noul = result["answers"]["prompt_injection"]["noul"]
        scored.append({
            **row,
            "jailbreak_noul": jailbreak_noul,
            "prompt_injection_noul": injection_noul,
            "s_raw": max(jailbreak_noul, injection_noul),
            "y": 1 if row["label"] == "attack" else 0,
        })
        if i % 100 == 0:
            print(f"  scored {i}/{len(rows)}")
    return scored


def logit(p: float) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def apply_temperature(s: float, T: float) -> float:
    return sigmoid(logit(s) / T)


def class_balanced_nll(scored: list[dict], T: float) -> float:
    n_attack = sum(1 for r in scored if r["y"] == 1)
    n_benign = sum(1 for r in scored if r["y"] == 0)
    total = 0.0
    for r in scored:
        p = apply_temperature(r["s_raw"], T)
        p = min(max(p, EPS), 1 - EPS)
        nll = -math.log(p) if r["y"] == 1 else -math.log(1 - p)
        w = 0.5 / n_attack if r["y"] == 1 else 0.5 / n_benign
        total += w * nll
    return total


def fit_temperature(scored: list[dict]) -> float:
    best_T, best_loss = 1.0, float("inf")
    for T in TEMPERATURE_GRID:
        loss = class_balanced_nll(scored, T)
        if loss < best_loss:
            best_T, best_loss = T, loss
    return best_T


def compute_ece(scored: list[dict], T: float) -> dict:
    """Standard 10-bin ECE on the combined set (predicted P(attack) vs
    accuracy=fraction attack in bin), plus the same bins' calibration
    gap attributed separately to attack rows and benign rows (i.e. how
    much calibration error each class actually experiences, using the
    combined-bin accuracy as ground truth)."""
    preds = [(apply_temperature(r["s_raw"], T), r["y"]) for r in scored]
    bins = [[] for _ in range(N_BINS)]
    for p, y in preds:
        idx = min(int(p * N_BINS), N_BINS - 1)
        bins[idx].append((p, y))

    n = len(preds)
    ece_combined = 0.0
    ece_attack_num, n_attack = 0.0, 0
    ece_benign_num, n_benign = 0.0, 0
    for b in bins:
        if not b:
            continue
        bin_conf = sum(p for p, _ in b) / len(b)
        bin_acc = sum(y for _, y in b) / len(b)
        gap = abs(bin_conf - bin_acc)
        ece_combined += (len(b) / n) * gap
        for p, y in b:
            if y == 1:
                ece_attack_num += gap
                n_attack += 1
            else:
                ece_benign_num += gap
                n_benign += 1

    return {
        "ece_combined": ece_combined,
        "ece_attack": ece_attack_num / n_attack if n_attack else None,
        "ece_benign": ece_benign_num / n_benign if n_benign else None,
        "n_attack": n_attack,
        "n_benign": n_benign,
    }


def main():
    rows = load_calibration_rows()
    n_attack = sum(1 for r in rows if r["label"] == "attack")
    n_benign = sum(1 for r in rows if r["label"] == "benign")
    print(f"Calibration split, L1/L2-blocked rows: {len(rows)} ({n_attack} attack, {n_benign} benign)")
    print("Class balance method: class-balanced weighting (0.5/n_class per row) - "
          f"n_benign={n_benign} is too small to subsample attacks down to and still fit a stable T")

    print("Scoring with Laya (jailbreak + prompt_injection noul, ~2s/row on CPU)...")
    scored = score_rows_with_laya(rows)
    with open(SCORES_OUT_PATH, "w", encoding="utf-8") as f:
        for r in scored:
            f.write(json.dumps(r) + "\n")
    print(f"Raw scores saved to {SCORES_OUT_PATH}")

    ece_before = compute_ece(scored, T=1.0)
    T_fitted = fit_temperature(scored)
    ece_after = compute_ece(scored, T=T_fitted)

    print(f"\nFitted temperature: T={T_fitted}")
    print(f"ECE before (T=1.0, Laya's shipped calibration): "
          f"combined={ece_before['ece_combined']:.4f}  "
          f"attack={ece_before['ece_attack']:.4f}  benign={ece_before['ece_benign']:.4f}")
    print(f"ECE after  (T={T_fitted}): "
          f"combined={ece_after['ece_combined']:.4f}  "
          f"attack={ece_after['ece_attack']:.4f}  benign={ece_after['ece_benign']:.4f}")

    out = {
        "temperature": T_fitted,
        "class_balance_method": "class_balanced_weighting",
        "n_calibration_rows": len(rows),
        "n_attack": n_attack,
        "n_benign": n_benign,
        "score_definition": "s = max(jailbreak.noul, prompt_injection.noul); P(benign) = 1 - sigmoid(logit(s)/T)",
        "ece_before": ece_before,
        "ece_after": ece_after,
        "temperature_grid_min": min(TEMPERATURE_GRID),
        "temperature_grid_max": max(TEMPERATURE_GRID),
    }
    with open(CALIBRATION_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nCalibration result written to {CALIBRATION_OUT_PATH}")


if __name__ == "__main__":
    main()
