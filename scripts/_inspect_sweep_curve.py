import json
rows = [json.loads(l) for l in open("data/laya_threshold_sweep.jsonl", encoding="utf-8")]
diverge = [r for r in rows if r["strict_recall_lost"] != r["effective_recall_lost"]]
print(f"thresholds where strict != effective: {len(diverge)}/{len(rows)}")
for t in [0.0, 0.1, 0.3, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.0]:
    r = next(x for x in rows if abs(x["t"]-t) < 1e-9)
    print(f"t={t:.2f}  strict={r['strict_recall_lost']*100:5.2f}%  effective={r['effective_recall_lost']*100:5.2f}%  "
          f"fpr_reduction={r['fpr_reduction']*100:5.1f}%  n_benign_overturned={r['n_benign_overturned']}/15")
