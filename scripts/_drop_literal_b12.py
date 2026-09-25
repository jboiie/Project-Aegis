import json
import re

text = open("data/spotcheck_literal_b12.md", encoding="utf-8").read()
entries = re.split(r"\n(?=\d+\. \*\*row_id\*\*)", text)
parsed = {}
for e in entries:
    m = re.match(r"(\d+)\. \*\*row_id\*\*: (\S+)\s+\*\*split\*\*: (\S+)\s+\*\*blocked_by\*\*: (\S+)\n(.*)", e, re.S)
    if not m:
        continue
    idx = int(m.group(1))
    prompt = m.group(5).strip("\n")
    # prompt lines are indented by 3 spaces per the writer script; strip leading spaces per line, drop trailing blank
    lines = [l[3:] if l.startswith("   ") else l for l in prompt.split("\n")]
    prompt_text = "\n".join(lines).rstrip("\n")
    parsed[idx] = prompt_text

drop_indices = set(range(1, 31)) | set(range(41, 51))
keep_indices = set(range(31, 41)) | set(range(51, 61))
assert len(drop_indices) == 40 and len(keep_indices) == 20
drop_prompts = {parsed[i] for i in drop_indices}

benign_rows = [json.loads(l) for l in open("data/benign_prompts.jsonl", encoding="utf-8")]
before = len(benign_rows)
matched = 0
kept = []
for r in benign_rows:
    if r["category"] == "literal_editing_instruction" and r.get("batch") in (1, 2) and r["prompt"] in drop_prompts:
        matched += 1
        continue
    kept.append(r)
print(f"benign_prompts.jsonl matched-for-drop: {matched}/40")
with open("data/benign_prompts.jsonl", "w", encoding="utf-8") as f:
    for r in kept:
        f.write(json.dumps(r) + "\n")
print(f"benign_prompts.jsonl: {before} -> {len(kept)}")

screen_rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
before2 = len(screen_rows)
matched2 = 0
kept2 = []
for r in screen_rows:
    if r.get("row_type") == "benign" and r.get("category") == "literal_editing_instruction" and r.get("batch") in (1, 2) and r["prompt"] in drop_prompts:
        matched2 += 1
        continue
    kept2.append(r)
print(f"laya_screen_results.jsonl matched-for-drop: {matched2}/40")
with open("data/laya_screen_results.jsonl", "w", encoding="utf-8") as f:
    for r in kept2:
        f.write(json.dumps(r) + "\n")
print(f"laya_screen_results.jsonl: {before2} -> {len(kept2)}")
