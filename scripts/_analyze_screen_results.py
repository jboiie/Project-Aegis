import json
from collections import defaultdict

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
attacks = [r for r in rows if r["row_type"] == "attack"]
benigns = [r for r in rows if r["row_type"] == "benign"]

print("=" * 70)
print("ATTACKS - per split, per wrapper type")
print("=" * 70)
for split in ("calibration", "sweep", "test"):
    split_attacks = [r for r in attacks if r["split"] == split]
    print(f"\n-- {split} -- total={len(split_attacks)}")
    for wrapper_type in ("template", "encoding", "labeled_eval_set"):
        rows_wt = [r for r in split_attacks if r["wrapper_type"] == wrapper_type]
        if not rows_wt:
            continue
        n = len(rows_wt)
        l1 = sum(1 for r in rows_wt if r["blocking_layer"] == "L1")
        l2 = sum(1 for r in rows_wt if r["blocking_layer"] == "L2")
        l3 = sum(1 for r in rows_wt if r["blocking_layer"] == "L3")
        l4 = sum(1 for r in rows_wt if r["blocking_layer"] == "L4")
        passed = sum(1 for r in rows_wt if r["blocking_layer"] is None)
        print(f"  {wrapper_type:<18} n={n:<5} L1={l1:<5} L2={l2:<5} L3={l3:<4} L4={l4:<4} passed_all={passed}")
    # totals
    n = len(split_attacks)
    l1 = sum(1 for r in split_attacks if r["blocking_layer"] == "L1")
    l2 = sum(1 for r in split_attacks if r["blocking_layer"] == "L2")
    l1_or_l2 = l1 + l2
    print(f"  {'TOTAL':<18} n={n:<5} L1={l1:<5} L2={l2:<5} L1+L2 blocked={l1_or_l2}")

print("\n" + "=" * 70)
print("BENIGN - per split, per category")
print("=" * 70)
for split in ("calibration", "sweep", "test"):
    split_benign = [r for r in benigns if r["split"] == split]
    print(f"\n-- {split} -- total={len(split_benign)}")
    categories = sorted(set(r["category"] for r in split_benign))
    total_l1 = total_l2 = 0
    for cat in categories:
        rows_c = [r for r in split_benign if r["category"] == cat]
        n = len(rows_c)
        l1 = sum(1 for r in rows_c if r["blocking_layer"] == "L1")
        l2 = sum(1 for r in rows_c if r["blocking_layer"] == "L2")
        total_l1 += l1
        total_l2 += l2
        if l1 or l2:
            print(f"  {cat:<28} n={n:<5} L1={l1:<4} L2={l2:<4}")
    print(f"  {'TOTAL':<28} n={len(split_benign):<5} L1={total_l1:<4} L2={total_l2:<4} L1+L2={total_l1+total_l2}")

print("\n" + "=" * 70)
print("KEY NUMBERS FOR THE EXPERIMENT")
print("=" * 70)
sweep_attacks = [r for r in attacks if r["split"] == "sweep"]
sweep_blocked = [r for r in sweep_attacks if r["blocking_layer"] in ("L1", "L2")]
print(f"Sweep split: {len(sweep_blocked)} attacks blocked by L1/L2 (the population the threshold rule operates on)")
print(f"  5% recall loss (MAX_RECALL_LOSS=0.05) = {len(sweep_blocked)*0.05:.1f} attacks "
      f"(i.e. at most {int(len(sweep_blocked)*0.05)} of these {len(sweep_blocked)} may be wrongly overturned)")

test_benign = [r for r in benigns if r["split"] == "test"]
test_benign_blocked = [r for r in test_benign if r["blocking_layer"] in ("L1", "L2")]
print(f"\nTest split: {len(test_benign_blocked)}/{len(test_benign)} benign rows blocked by L1/L2 "
      f"(the population laya_eval.py's FPR-reduction table operates on)")

cal_attacks = [r for r in attacks if r["split"] == "calibration"]
cal_blocked = [r for r in cal_attacks if r["blocking_layer"] in ("L1", "L2")]
cal_benign = [r for r in benigns if r["split"] == "calibration"]
cal_benign_blocked = [r for r in cal_benign if r["blocking_layer"] in ("L1", "L2")]
print(f"\nCalibration split (for laya_calibrate.py): {len(cal_blocked)} attacks blocked, "
      f"{len(cal_benign_blocked)} benign blocked")
