import json
import sys

path = sys.argv[1]
with open(path) as f:
    rows = [json.loads(l) for l in f]

from collections import Counter
print(f"n={len(rows)}")
print("outcome counts:", dict(Counter(r["outcome"] for r in rows)))
for r in rows:
    print(f"  outcome={r['outcome']:<16} iters_to_bypass={r['metadata'].get('iterations_to_bypass')} "
          f"fallback={r['metadata'].get('attacker_fallback_count')} judge_score={r['judge_score']} "
          f"errored={r['errored']}")
