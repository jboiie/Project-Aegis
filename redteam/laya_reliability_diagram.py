"""Reliability diagram: predicted confidence vs. actual accuracy, pre
and post temperature scaling, attacks and benign plotted separately.
Uses the cleaned calibration split (data/laya_calibration_scores.jsonl,
s_raw + y already computed - no Laya re-invocation needed).

Per step-5 item 6 (calibration wording): this diagram is diagnostic,
not a claim that Laya's confidence is a calibrated probability - see
laya_calibrate.py's docstring and PROJECT_DESC.md for the "ranking +
empirically chosen threshold, not calibration" framing.
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPS = 1e-6
N_BINS = 10


def logit(p):
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-z))


def apply_temperature(s, T):
    return sigmoid(logit(s) / T)


def bin_reliability(pairs: list[tuple[float, int]], n_bins: int = N_BINS):
    """pairs = [(predicted_p_attack, y), ...]. Returns (bin_centers, bin_confidence,
    bin_accuracy, bin_counts) - only for non-empty bins."""
    bins = [[] for _ in range(n_bins)]
    for p, y in pairs:
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, y))
    centers, confs, accs, counts = [], [], [], []
    for i, b in enumerate(bins):
        if not b:
            continue
        centers.append((i + 0.5) / n_bins)
        confs.append(sum(p for p, _ in b) / len(b))
        accs.append(sum(y for _, y in b) / len(b))
        counts.append(len(b))
    return centers, confs, accs, counts


def main():
    """Accuracy (fraction actually attack) only has meaning when a bin
    mixes both classes, so the reliability curve itself is computed on
    the COMBINED calibration set. "Attacks and benign separately" is
    then shown as a rug of each class's individual predicted-confidence
    values along the x-axis of that same curve, so you can see where
    each class's mass actually sits relative to the (combined) curve -
    a per-class-only accuracy would be trivially 1.0 for attack rows
    and 0.0 for benign rows and wouldn't show anything."""
    with open(os.path.join(_REPO_ROOT, "data", "laya_calibration.json"), encoding="utf-8") as f:
        cal = json.load(f)
    T = cal["temperature"]

    scored = [json.loads(l) for l in open(
        os.path.join(_REPO_ROOT, "data", "laya_calibration_scores.jsonl"), encoding="utf-8")]
    all_pairs = [(r["s_raw"], r["y"], r["label"]) for r in scored]

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    panels = [("pre-temperature (T=1.0)", 1.0, axes[0]),
              (f"post-temperature (T={T:.2f})", T, axes[1])]

    for title, temp, ax in panels:
        transformed = [(apply_temperature(s, temp), y) for s, y, _ in all_pairs]
        centers, confs, accs, counts = bin_reliability(transformed)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="perfect calibration")
        if confs:
            ax.scatter(confs, accs, s=[20 + 4 * c for c in counts], alpha=0.8,
                       color="tab:blue", zorder=3, label="combined reliability curve")
            ax.plot(confs, accs, alpha=0.4, color="tab:blue", zorder=2)

        attack_x = [apply_temperature(s, temp) for s, y, label in all_pairs if label == "attack"]
        benign_x = [apply_temperature(s, temp) for s, y, label in all_pairs if label == "benign"]
        ax.scatter(attack_x, [-0.03] * len(attack_x), marker="|", color="tab:red",
                   alpha=0.3, label=f"attack rows (n={len(attack_x)})", clip_on=False)
        ax.scatter(benign_x, [1.03] * len(benign_x), marker="|", color="tab:green",
                   alpha=0.6, s=80, label=f"benign rows (n={len(benign_x)})", clip_on=False)

        ax.set_xlim(0, 1)
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel("predicted P(attack)")
        ax.set_ylabel("actual fraction attack (bin accuracy, combined population)")
        ax.set_title(title)
        ax.legend(loc="lower right", fontsize=8)

    fig.suptitle(
        "Laya reliability diagram - calibration split (cleaned), n=1198 (1191 attack, 7 benign)\n"
        "Diagnostic only: the overturn decision uses ranking + an empirically\n"
        "chosen threshold, NOT a claim that this confidence is calibrated",
        fontsize=10,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.88])

    out_path = os.path.join(_REPO_ROOT, "data", "laya_reliability_diagram.png")
    fig.savefig(out_path, dpi=150)
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
