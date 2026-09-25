import json
from collections import Counter

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
benign = [r for r in rows if r["row_type"] == "benign"]

for split in ("calibration", "sweep", "test"):
    sb = [r for r in benign if r["split"] == split]
    print(f"\n-- {split} -- total benign={len(sb)}")
    by = Counter()
    blocked = Counter()
    for r in sb:
        key = (r["category"], r.get("batch"))
        by[key] += 1
        if r["blocking_layer"] in ("L1", "L2"):
            blocked[key] += 1
    for key in sorted(by):
        cat, batch = key
        if by[key] == 0:
            continue
        print(f"  {cat:<28} batch={batch}  n={by[key]:<4} blocked={blocked.get(key,0)}")
    total_blocked = sum(1 for r in sb if r["blocking_layer"] in ("L1","L2"))
    print(f"  TOTAL blocked: {total_blocked}/{len(sb)}")
