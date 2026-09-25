import json
import re

# Per-call refusal rate from the raw log.
log_path = r"C:\Users\jai19\AppData\Local\Temp\claude\c--Programming-Projects-argus\efbf361f-3459-4f2c-8068-1934f085b5b7\tasks\bbccs8ujw.output"
n_refusals = 0
n_attacker_calls = 0
with open(log_path, encoding="utf-8", errors="ignore") as f:
    for line in f:
        if "attacker_refusal_detected" in line:
            n_refusals += 1
        if "role=attacker" in line:
            n_attacker_calls += 1

print(f"Per-call: {n_refusals} refusals / {n_attacker_calls} attacker calls = {n_refusals/n_attacker_calls:.1%}")

# Per-iteration: how many iterations exhausted all 3 attempts and fell
# back (persistent refusal), vs how many iterations ran total. We don't
# export per-iteration rows, only per-attempt final results with an
# attacker_fallback_count in metadata (this is the OLD name for fallback
# usage - includes both truncated-reasoning and persistent-refusal
# fallbacks, can't fully separate post-hoc from the export alone, but the
# overwhelming majority of fallback triggers here are refusal-based per
# the log above showing near-zero truncated-reasoning events this run).
total_fallback = 0
total_iterations_used = 0
for l in open(r"C:/Programming/Projects/aegis/data/pair_rerun_20_fixed_attacker.jsonl", encoding="utf-8"):
    r = json.loads(l)
    total_fallback += r["metadata"].get("attacker_fallback_count", 0)
    iters = r["metadata"].get("iterations_to_bypass")
    total_iterations_used += iters if iters else 5  # exhausted max_iterations if never bypassed

print(f"Per-iteration (max_iterations=5 default when never bypassed): "
      f"{total_fallback} iterations fell back to canned template / {total_iterations_used} total iterations run "
      f"= {total_fallback/total_iterations_used:.1%}")
