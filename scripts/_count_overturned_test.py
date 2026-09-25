import json
scores = [json.loads(l) for l in open("data/laya_scores_test.jsonl", encoding="utf-8")]
t = 0.69
overturned = [r for r in scores if r["label"]=="attack" and r["laya_confidence"]>=t]
print(f"overturned test attacks at t={t}: {len(overturned)}")
for r in overturned[:5]:
    print(" ", r["wrapper_type"], r.get("goal"), r["laya_confidence"])
