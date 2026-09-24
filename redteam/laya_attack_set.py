"""Builds the attack set for the Laya second-stage experiment.

Attack set = template wrappers over AdvBench goals + encoding wrappers
over AdvBench goals + the 25 real labeled attacks in
data/labeled_eval_set.jsonl. No PAIR candidates - PAIR is dropped from
ASR claims (90.4% attacker refusal rate, stopping rule triggered, see
PROJECT_DESC.md).

Split discipline: AdvBench-wrapped rows are split by GOAL, not by row -
every wrapper variant of the same goal (5 templates + 5 encodings = 10
rows) lands in the same split, so the experiment never trains/calibrates
on one wrapping of a goal and tests on another wrapping of the SAME goal
(which would leak goal-specific signal across the split boundary).
labeled_eval_set.jsonl's 25 rows are standalone prompts with no shared
goal structure, so they split by row using the same stratified ratios.

No Groq calls here - this only builds prompts and labels. The engine.py
verdicts and Laya's verdict are computed separately by
laya_second_stage.py, run locally.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redteam.attacks.template import TEMPLATES, _load_advbench_sample
from redteam.attacks.encoding import ENCODERS

SPLIT_RATIOS = {"calibration": 0.30, "sweep": 0.40, "test": 0.30}
LABELED_EVAL_SET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                       "data", "labeled_eval_set.jsonl")
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "laya_attack_set.jsonl")


def _assign_split_by_key(rows: list[dict], key_fn) -> None:
    """Groups rows by key_fn(row), shuffles the GROUPS (not individual
    rows), and assigns every row in a group to the same split - the goal-
    level (not row-level) split discipline this module exists for."""
    groups: dict = {}
    for r in rows:
        groups.setdefault(key_fn(r), []).append(r)
    keys = list(groups.keys())
    random.shuffle(keys)
    n = len(keys)
    n_cal = round(n * SPLIT_RATIOS["calibration"])
    n_sweep = round(n * SPLIT_RATIOS["sweep"])
    for i, k in enumerate(keys):
        split = "calibration" if i < n_cal else ("sweep" if i < n_cal + n_sweep else "test")
        for r in groups[k]:
            r["split"] = split


def build_advbench_wrapped_rows() -> list[dict]:
    goals = _load_advbench_sample()
    rows = []
    for goal in goals:
        for template in TEMPLATES:
            prompt = template["prompt"].format(harmful_request=goal)
            rows.append({"prompt": prompt, "label": "attack", "wrapper_type": "template",
                         "template_name": template["name"], "goal": goal})
        for encoding_name, encoder in ENCODERS.items():
            encoded = encoder(goal)
            rows.append({"prompt": encoded, "label": "attack", "wrapper_type": "encoding",
                         "encoding_name": encoding_name, "goal": goal})
    _assign_split_by_key(rows, key_fn=lambda r: r["goal"])
    return rows


def build_labeled_eval_set_rows() -> list[dict]:
    rows = []
    with open(LABELED_EVAL_SET_PATH, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["label"] == "attack":
                rows.append({"prompt": row["prompt"], "label": "attack",
                             "wrapper_type": "labeled_eval_set", "goal": None})
    # Row-level split - no shared goal structure to group by here.
    _assign_split_by_key(rows, key_fn=lambda r: id(r))
    return rows


def main():
    random.seed(42)
    advbench_rows = build_advbench_wrapped_rows()
    labeled_rows = build_labeled_eval_set_rows()
    all_rows = advbench_rows + labeled_rows

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r) + "\n")

    print(f"Total attack rows: {len(all_rows)}")
    print(f"  AdvBench-wrapped: {len(advbench_rows)} (30 goals x 10 wrappers)")
    print(f"  labeled_eval_set.jsonl: {len(labeled_rows)}")
    print(f"  PAIR candidates: 0 (dropped per stopping rule)")

    print("\nPer split, per wrapper type:")
    for split in ("calibration", "sweep", "test"):
        split_rows = [r for r in all_rows if r["split"] == split]
        by_type: dict[str, int] = {}
        for r in split_rows:
            by_type[r["wrapper_type"]] = by_type.get(r["wrapper_type"], 0) + 1
        n_goals = len(set(r["goal"] for r in split_rows if r["goal"] is not None))
        print(f"  {split}: {len(split_rows)} total, {n_goals} distinct AdvBench goals, breakdown={by_type}")

    print(f"\nWritten to {OUT_PATH}")


if __name__ == "__main__":
    main()
