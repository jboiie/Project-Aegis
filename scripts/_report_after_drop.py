import json
from collections import Counter

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
test_benign = [r for r in rows if r["row_type"] == "benign" and r["split"] == "test"]
print(f"test benign total: {len(test_benign)}")
by = Counter()
blocked_by = Counter()
for r in test_benign:
    key = (r["category"], r.get("batch"))
    by[key] += 1
    if r["blocking_layer"] in ("L1", "L2"):
        blocked_by[key] += 1

for key in sorted(by):
    cat, batch = key
    print(f"  {cat:<28} batch={batch}  n={by[key]:<4} blocked={blocked_by.get(key,0)}")

total_blocked = sum(1 for r in test_benign if r["blocking_layer"] in ("L1","L2"))
print(f"\ntotal test blocked benign: {total_blocked}/{len(test_benign)}")
