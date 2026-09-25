import os
import sys
from collections import Counter

sys.path.insert(0, "C:/Programming/Projects/aegis")
from dotenv import load_dotenv
load_dotenv("C:/Programming/Projects/aegis/.env")
from supabase import create_client

client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
resp = client.table("aegis_events").select("*").order("timestamp", desc=True).limit(500).execute()
rows = resp.data
print(f"Fetched {len(rows)} most recent aegis_events rows.")
if not rows:
    raise SystemExit

print("Columns:", list(rows[0].keys()))
print("\nMost recent timestamp:", rows[0].get("timestamp"))
print("Oldest in this batch:", rows[-1].get("timestamp"))

blocked_counter = Counter(r.get("blocked") for r in rows)
print("\nblocked value counts (last 500):", dict(blocked_counter))

reason_counter = Counter((r.get("blocked_reason") or "")[:60] for r in rows if r.get("blocked"))
print("\nTop blocked_reasons:")
for reason, count in reason_counter.most_common(10):
    print(f"  {count:4d}  {reason!r}")

# Look for rows whose content/blocked_reason suggests a dead-model API error
error_like = [r for r in rows if "error" in (r.get("blocked_reason") or "").lower()
              or "Internal Server" in (r.get("blocked_reason") or "")]
print(f"\nRows with an error-like blocked_reason: {len(error_like)}")
for r in error_like[:10]:
    print(f"  {r.get('timestamp')}  blocked={r.get('blocked')}  reason={r.get('blocked_reason')!r}")

print("\n--- model field breakdown ---")
model_counter = Counter(r.get("model") for r in rows)
for model, count in model_counter.most_common():
    print(f"  {count:4d}  {model!r}")

print("\n--- per-model blocked breakdown ---")
by_model = {}
for r in rows:
    m = r.get("model")
    by_model.setdefault(m, Counter())[r.get("blocked")] += 1
for m, c in by_model.items():
    print(f"  {m!r}: {dict(c)}")

print("\n--- oldest and newest row per distinct model ---")
for m in model_counter:
    matching = [r for r in rows if r.get("model") == m]
    ts = sorted(r.get("timestamp") for r in matching)
    print(f"  {m!r}: {ts[0]} .. {ts[-1]} (n={len(matching)})")
