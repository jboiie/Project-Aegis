import json
import re

BARE_PATTERN = re.compile(r"(?i)jailbreak(ed)?")

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
for split in ("sweep", "test"):
    l1 = [r for r in rows if r["split"]==split and r["blocking_layer"]=="L1"]
    bare = []
    for r in l1:
        m = re.search(r"Matched known attack pattern: '(.+)'$", r["blocked_reason"])
        matched = m.group(1) if m else ""
        if re.fullmatch(r"(?i)jailbreak(ed)?", matched):
            bare.append(r)
    n_attack = sum(1 for r in bare if r["label"]=="attack")
    n_benign = sum(1 for r in bare if r["label"]=="benign")
    print(f"{split}: L1-blocked total={len(l1)}, bare-jailbreak-keyword={len(bare)} (attack={n_attack}, benign={n_benign})")
    cats = {}
    for r in bare:
        cats[r.get("category") or r.get("wrapper_type")] = cats.get(r.get("category") or r.get("wrapper_type"),0)+1
    print("  by category/wrapper:", cats)
