"""Silver move prep, baseline check (read-only, 2026-11-23).

1. Do the local TM/Music/sql/nightly files match the copies the job actually runs (workspace music_nightly/)?
   The dry run must start from what runs tonight, not from a stale local copy.
2. What can Dan's groups do in nonprod gold and nonprod silver (the dry run writes there)?
"""
import base64
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dbx_api import call_api, run_sql

WAREHOUSE_ID: str = "dbb3244d6fa2f0fc"
LOCAL_NIGHTLY_DIR: Path = Path.home() / "TM" / "Music" / "sql" / "nightly"
WORKSPACE_DIR: str = "/Users/dan.chamberlin@ticketmaster.com/music_nightly"

listing = call_api("GET", "/api/2.0/workspace/list?path=" + urllib.parse.quote(WORKSPACE_DIR)).get("objects", [])
workspace_names = sorted(os.path.basename(item["path"]) for item in listing)
local_names = sorted(p.name for p in LOCAL_NIGHTLY_DIR.glob("*.sql"))
print("workspace files:", workspace_names)
print("local only:", sorted(set(local_names) - set(workspace_names)),
      "| workspace only:", sorted(set(workspace_names) - set(local_names)))
for file_name in sorted(set(local_names) & set(workspace_names)):
    exported = call_api("GET", "/api/2.0/workspace/export?format=SOURCE&path="
                        + urllib.parse.quote(f"{WORKSPACE_DIR}/{file_name}"))
    workspace_text = base64.b64decode(exported["content"]).decode("utf-8").replace("\r\n", "\n")
    local_text = (LOCAL_NIGHTLY_DIR / file_name).read_text(encoding="utf-8").replace("\r\n", "\n")
    print(f"  {file_name}: {'same' if workspace_text.strip() == local_text.strip() else 'DIFFERENT'}")

_, grant_rows = run_sql(WAREHOUSE_ID, """
    SELECT catalog_name, schema_name, grantee, concat_ws(', ', sort_array(collect_set(privilege_type))) privileges
    FROM system.information_schema.schema_privileges
    WHERE catalog_name IN ('nonprod_shared_gold', 'nonprod_shared_silver') AND schema_name LIKE 'central_analytics%'
      AND grantee IN ('team_tm_central_analytics_users', 'cds-analytics-users', 'central-analytics-users', 'account users')
    GROUP BY 1, 2, 3 ORDER BY 1, 3""")
print("\nnonprod grants for Dan's groups:")
for row in grant_rows:
    print("  ", " | ".join(row))
