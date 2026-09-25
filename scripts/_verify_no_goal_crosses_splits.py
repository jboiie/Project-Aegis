import json
from collections import defaultdict

goal_splits = defaultdict(set)
for l in open("data/laya_attack_set.jsonl", encoding="utf-8"):
    r = json.loads(l)
    if r["goal"] is not None:
        goal_splits[r["goal"]].add(r["split"])

violations = {g: s for g, s in goal_splits.items() if len(s) > 1}
print(f"{len(goal_splits)} distinct AdvBench goals checked.")
print(f"Goals crossing splits: {len(violations)}")
if violations:
    for g, s in violations.items():
        print(f"  VIOLATION: {g!r} in splits {s}")
else:
    print("Confirmed: every goal's wrapper variants land in exactly one split.")
