import json

for l in open("data/pair_rerun_20.jsonl", encoding="utf-8"):
    r = json.loads(l)
    if r["outcome"] == "bypassed":
        print(json.dumps(r, indent=2))
        print("=" * 60)
