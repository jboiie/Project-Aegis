import os
from dotenv import load_dotenv
load_dotenv("C:/Programming/Projects/aegis/.env")
from supabase import create_client

client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
# Supabase's Python client has no raw-SQL execute; use the SQL editor's
# exposed RPC if available, otherwise fall back to the REST admin endpoint.
sql = "ALTER TABLE aegis_events ADD COLUMN IF NOT EXISTS errored BOOLEAN NOT NULL DEFAULT false;"
try:
    result = client.rpc("exec_sql", {"sql": sql}).execute()
    print("Applied via rpc exec_sql:", result)
except Exception as exc:
    print(f"rpc exec_sql not available ({type(exc).__name__}: {exc}) - need to run this SQL manually in the Supabase SQL editor:")
    print(sql)
