import json
rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
for split in ("sweep", "test"):
    s = [r for r in rows if r["split"]==split and r["blocking_layer"]=="L2"]
    a = sum(1 for r in s if r["label"]=="attack")
    b = sum(1 for r in s if r["label"]=="benign")
    print(split, "L2 blocked total", len(s), "attack", a, "benign", b)
