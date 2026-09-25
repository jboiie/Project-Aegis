import json
scores = [json.loads(l) for l in open("data/laya_scores_test.jsonl", encoding="utf-8")]
t = 0.69
overturned = [r for r in scores if r["laya_confidence"] >= t]
from collections import Counter
c = Counter((r["label"], r["blocking_layer"]) for r in overturned)
print("Laya test overturns by (label, blocking_layer):", dict(c))
total = Counter((r["label"], r["blocking_layer"]) for r in scores)
print("totals blocked by (label, blocking_layer):", dict(total))
