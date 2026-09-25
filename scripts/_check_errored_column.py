import os
from dotenv import load_dotenv
load_dotenv("C:/Programming/Projects/aegis/.env")
from supabase import create_client

client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
try:
    resp = client.table("aegis_events").select("errored").limit(1).execute()
    print("errored column EXISTS on the live table. Sample:", resp.data)
except Exception as exc:
    print("errored column query FAILED (column likely does not exist live):")
    print(f"  {type(exc).__name__}: {exc}")
