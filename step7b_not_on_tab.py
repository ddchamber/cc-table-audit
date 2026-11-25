"""Step 7b: for the music_* names the live check found that are not on Dan's tab, show whether each
exists as a table (any catalog) and the exact job-file lines that name it. Read-only."""
import base64
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import call_api, run_sql

WAREHOUSE_ID: str = "dbb3244d6fa2f0fc"
NIGHTLY_JOB_ID: str = "489488962317323"
NAMES_NOT_ON_TAB: list[str] = [
    "music_artist_lookup_step17", "music_artist_lookup_step18", "music_asu_event_signups_step19",
    "music_asu_tour_conversion_by_tour", "music_asu_tour_conversion_by_tour_nightly",
    "music_benchmark_events_step21", "music_dashboard_guide", "music_event_phase_summary_step17",
    "music_str_daily_step17",
]

in_list = ",".join(f"'{name}'" for name in NAMES_NOT_ON_TAB)
columns, rows = run_sql(WAREHOUSE_ID, f"""
    SELECT table_catalog, table_schema, table_name, table_type, table_owner, created, last_altered
    FROM system.information_schema.tables WHERE table_name IN ({in_list}) ORDER BY table_name""")
print("EXISTING TABLES")
for row in rows:
    print("  ", " | ".join(str(value) for value in row))

print("\nJOB FILE LINES")
job = call_api("GET", f"/api/2.1/jobs/get?job_id={NIGHTLY_JOB_ID}")
for task in job["settings"]["tasks"]:
    file_path = (task.get("sql_task") or {}).get("file", {}).get("path")
    if not file_path:
        continue
    exported = call_api("GET", "/api/2.0/workspace/export?format=SOURCE&path="
                        + urllib.parse.quote(file_path.removeprefix("/Workspace")))
    file_text = base64.b64decode(exported.get("content", "")).decode("utf-8", errors="ignore")
    for line_number, line in enumerate(file_text.splitlines(), 1):
        lowered = line.lower()
        # Match whole names only, so music_artist_lookup_step17 does not also hit _step17_live.
        for name in NAMES_NOT_ON_TAB:
            index = lowered.find(name)
            if index >= 0 and not (lowered[index + len(name):index + len(name) + 1].isalnum()
                                   or lowered[index + len(name):index + len(name) + 1] == "_"):
                print(f"   {os.path.basename(file_path)}:{line_number}: {line.strip()[:150]}")
                break
