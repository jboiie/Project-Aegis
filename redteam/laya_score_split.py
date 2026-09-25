"""Scores one split's L1/L2-blocked rows with Laya (jailbreak +
prompt_injection noul), applying the temperature fit by laya_calibrate.py.
Requires the laya-bench conda env. Writes data/laya_scores_<split>.jsonl.

Usage: conda run -n laya-bench python redteam/laya_score_split.py --split sweep
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redteam.laya_second_stage import laya_guard_verdict, load_temperature

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN_RESULTS_PATH = os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=["calibration", "sweep", "test"])
    args = parser.parse_args()

    out_path = os.path.join(_REPO_ROOT, "data", f"laya_scores_{args.split}.jsonl")
    temperature = load_temperature()
    print(f"Using temperature={temperature} from laya_calibrate.py")

    rows = [json.loads(l) for l in open(SCREEN_RESULTS_PATH, encoding="utf-8")]
    rows = [r for r in rows if r["split"] == args.split and r["blocking_layer"] in ("L1", "L2")]
    n_attack = sum(1 for r in rows if r["label"] == "attack")
    n_benign = sum(1 for r in rows if r["label"] == "benign")
    print(f"{args.split} split, L1/L2-blocked: {len(rows)} ({n_attack} attack, {n_benign} benign)")

    results = []
    for i, row in enumerate(rows):
        verdict = laya_guard_verdict(row["prompt"], temperature=temperature)
        results.append({**row, "row_index": i, "laya_confidence": verdict.confidence})
        if (i + 1) % 100 == 0:
            print(f"  scored {i + 1}/{len(rows)}")

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
