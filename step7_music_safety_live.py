"""Step 7 (2026-11-23): live safety check for the Music dashboard before any verdict is acted on.

Question: does anything the TM Music Post-Onsale Performance dashboard depends on today carry a
Delete or Move verdict that would break it? Read-only. Pulls everything live (not the 11-18 facts),
because the Music project changed after the audit ran:
  1. the dashboard's dataset SQL (published definition),
  2. the Music Genie space definition,
  3. the music-dashboard-nightly job: task list and every SQL file it runs,
  4. lineage reads of each Music object in the last 7 days (who and what touched it since the audit).
Output: facts/music_safety_live.json and a printed table, one line per Music object.
"""
import base64
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import call_api, run_sql

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
WAREHOUSE_ID: str = "dbb3244d6fa2f0fc"
MUSIC_DASHBOARD_ID: str = "01f1a18b81b01d91b6441a8fa3879ed7"
MUSIC_GENIE_SPACE_ID: str = "01f1ad736203170b88b764d2dc45bc80"
NIGHTLY_JOB_ID: str = "489488962317323"
# Matches any music_* name, including tables NOT on the audit tab, so a new dependency is caught too.
MUSIC_NAME_PATTERN = re.compile(r"\b((?:[a-z0-9_]+\.){0,2}music_[a-z0-9_]+)\b", re.IGNORECASE)


def music_names_in(text: str) -> set[str]:
    return {match.group(1).lower().split(".")[-1] for match in MUSIC_NAME_PATTERN.finditer(text or "")}


def main() -> None:
    verdicts: dict[str, dict] = {}
    with open(os.path.join(AUDIT_FOLDER, "out", "dan_chamberlin_audit_fact_checked.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            table_name = row["full_name"].split(".")[-1]
            if table_name.startswith("music"):
                verdicts[table_name] = row

    dependencies: dict[str, set[str]] = {}

    def add_dependency(table_name: str, source_label: str) -> None:
        dependencies.setdefault(table_name, set()).add(source_label)

    # 1. Dashboard datasets.
    dashboard = call_api("GET", f"/api/2.0/lakeview/dashboards/{MUSIC_DASHBOARD_ID}")
    serialized_dashboard = json.loads(dashboard.get("serialized_dashboard") or "{}")
    for dataset in serialized_dashboard.get("datasets", []):
        dataset_sql = "".join(dataset.get("queryLines") or [dataset.get("query", "")])
        for table_name in music_names_in(dataset_sql):
            add_dependency(table_name, "dashboard")
    print("dashboard:", dashboard.get("display_name"), "| updated", dashboard.get("update_time"),
          "| datasets", len(serialized_dashboard.get("datasets", [])))

    # 2. Genie space.
    try:
        genie_space = call_api("GET", f"/api/2.0/genie/spaces/{MUSIC_GENIE_SPACE_ID}?include_serialized_space=true")
        for table_name in music_names_in(json.dumps(genie_space)):
            add_dependency(table_name, "genie")
        print("genie:", genie_space.get("title"))
    except urllib.error.HTTPError as http_error:
        print("genie: unreadable, HTTP", http_error.code)

    # 3. Nightly job: every SQL file it runs, labelled by file so a needed edit is traceable.
    job = call_api("GET", f"/api/2.1/jobs/get?job_id={NIGHTLY_JOB_ID}")
    print("job:", job["settings"]["name"], "| run as", job.get("run_as_user_name"),
          "| tasks", len(job["settings"].get("tasks", [])))
    for task in job["settings"].get("tasks", []):
        file_path = (task.get("sql_task") or {}).get("file", {}).get("path")
        if not file_path:
            continue
        workspace_path = file_path.removeprefix("/Workspace")
        exported = call_api("GET", "/api/2.0/workspace/export?format=SOURCE&path=" + urllib.parse.quote(workspace_path))
        file_text = base64.b64decode(exported.get("content", "")).decode("utf-8", errors="ignore")
        for table_name in music_names_in(file_text):
            add_dependency(table_name, "job:" + os.path.basename(file_path).split("_")[0])

    # 4. Reads in the last 7 days, other than Sachin's crawl, by entity type.
    _, recent_rows = run_sql(WAREHOUSE_ID, """
        SELECT source_table_name, concat_ws(', ', collect_set(coalesce(entity_type, 'ad hoc'))) read_via,
               concat_ws(', ', collect_set(split(created_by, '@')[0])) readers, max(event_date) last_read
        FROM system.access.table_lineage
        WHERE event_date >= current_date() - 7
          AND source_table_catalog = 'prod_shared_gold' AND source_table_schema = 'central_analytics_crd'
          AND source_table_name LIKE 'music%' AND created_by NOT LIKE 'sachin.dewangan%'
        GROUP BY 1""")
    recent_reads: dict[str, dict] = {r[0]: {"read_via": r[1], "readers": r[2], "last_read": r[3]} for r in recent_rows}

    all_names = sorted(set(verdicts) | set(dependencies))
    results: list[dict] = []
    for table_name in all_names:
        verdict = verdicts.get(table_name, {}).get("my_call", "NOT ON TAB")
        used_by = sorted(dependencies.get(table_name, set()))
        live_use = any(u in ("dashboard", "genie") or u.startswith("job:") for u in used_by)
        # Unsafe = something live uses it and the verdict removes it.
        status = "UNSAFE" if live_use and verdict == "Delete" else ("CHECK" if verdict == "NOT ON TAB" else "ok")
        results.append({"table": table_name, "verdict": verdict, "used_by": used_by,
                        "reads_7d": recent_reads.get(table_name), "status": status})
        print(f"{status:6} | {verdict:14} | {table_name:42} | {', '.join(used_by) or '-'} | "
              f"{(recent_reads.get(table_name) or {}).get('readers', '-')}")

    with open(os.path.join(AUDIT_FOLDER, "facts", "music_safety_live.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, default=str)
    print("\nUNSAFE:", sum(r["status"] == "UNSAFE" for r in results),
          "| not on tab:", [r["table"] for r in results if r["verdict"] == "NOT ON TAB"])


if __name__ == "__main__":
    main()
