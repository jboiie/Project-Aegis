import json
import random

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
b3 = [r for r in rows if r.get("batch") == 3]
print(f"batch3 total screened: {len(b3)}")
for cat in ("security_education", "literal_editing_instruction"):
    c = [r for r in b3 if r["category"] == cat]
    l1 = sum(1 for r in c if r["blocking_layer"] == "L1")
    l2 = sum(1 for r in c if r["blocking_layer"] == "L2")
    print(f"  {cat}: n={len(c)} L1={l1} L2={l2} blocked={l1+l2}")

test_benign = [r for r in rows if r["row_type"] == "benign" and r["split"] == "test"]
blocked = [r for r in test_benign if r["blocking_layer"] in ("L1", "L2")]
print(f"\ntest split benign total now: {len(test_benign)}, blocked by L1/L2: {len(blocked)}")

random.seed(123)
sample = random.sample(b3, 30)
print("\n--- random 30 spot-check ---")
for r in sample:
    print(f"[{r['category']}] blocked={r['blocking_layer']} :: {r['prompt']}")
