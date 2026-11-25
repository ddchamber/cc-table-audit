"""Step 2: gather live facts for the 95 objects (read-only). Writes CSVs/JSON into facts/.

Q1 metadata and comments, Q2 readers (90 days, per reader so exclusions stay visible),
Q3 upstream and writers (365 days), Q4 writer jobs and 30-day run health,
Q5 dashboards (name and dataset SQL) and Genie spaces (full-name match).
"""
import csv
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import call_api, run_sql

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
FACTS_FOLDER: str = os.path.join(AUDIT_FOLDER, "facts")
WAREHOUSE_ID: str = "dbb3244d6fa2f0fc"


def write_csv(file_name: str, column_names: list[str], rows: list[list]) -> None:
    with open(os.path.join(FACTS_FOLDER, file_name), "w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(column_names)
        writer.writerows(rows)
    print(f"{file_name}: {len(rows)} rows")


def main() -> None:
    os.makedirs(FACTS_FOLDER, exist_ok=True)
    with open(os.path.join(AUDIT_FOLDER, "objects.csv"), encoding="utf-8") as objects_file:
        full_names: list[str] = [row["full_name"] for row in csv.DictReader(objects_file)]
    values_list: str = ",\n".join(
        "('{}','{}','{}')".format(*full_name.split(".")) for full_name in full_names)

    q1_sql = f"""WITH o(c,s,t) AS (VALUES {values_list})
SELECT concat_ws('.',t.table_catalog,t.table_schema,t.table_name) full_name, t.table_type, t.table_owner,
       t.created, t.created_by, t.last_altered, t.last_altered_by, t.comment
FROM o JOIN system.information_schema.tables t
  ON t.table_catalog=o.c AND t.table_schema=o.s AND t.table_name=o.t"""
    write_csv("q1_metadata.csv", *run_sql(WAREHOUSE_ID, q1_sql))

    # One row per object x reader x access path, so the review can drop Dan, Sachin's crawl and
    # service-account sweeps by looking, instead of trusting a pre-filtered count.
    q2_sql = f"""WITH o(c,s,t) AS (VALUES {values_list})
SELECT l.source_table_full_name full_name, l.created_by reader, l.entity_type read_via,
       count(*) read_events, count(DISTINCT l.event_date) read_days,
       min(l.event_date) first_read, max(l.event_date) last_read,
       concat_ws(', ', slice(array_sort(collect_set(l.target_table_full_name)), 1, 12)) feeds_tables,
       concat_ws(', ', slice(array_sort(collect_set(l.entity_id)), 1, 8)) entity_ids,
       concat_ws(', ', slice(array_sort(collect_set(cast(l.event_date AS string))), 1, 12)) read_dates
FROM system.access.table_lineage l JOIN o
  ON l.source_table_catalog=o.c AND l.source_table_schema=o.s AND l.source_table_name=o.t
WHERE l.event_date >= current_date()-90
GROUP BY 1,2,3"""
    write_csv("q2_readers_90d.csv", *run_sql(WAREHOUSE_ID, q2_sql))

    q3_sql = f"""WITH o(c,s,t) AS (VALUES {values_list})
SELECT l.target_table_full_name full_name, max(l.event_date) last_write, count(DISTINCT l.event_date) write_days,
  concat_ws(', ', collect_set(l.created_by)) written_by,
  concat_ws(', ', collect_set(l.entity_type)) written_via,
  concat_ws(', ', collect_set(CASE WHEN l.entity_type='JOB' THEN l.entity_id END)) writer_job_ids,
  concat_ws(', ', collect_set(CASE WHEN l.entity_type='NOTEBOOK' THEN l.entity_id END)) writer_notebook_ids,
  concat_ws(', ', slice(array_sort(collect_set(l.source_table_full_name)),1,20)) built_from
FROM system.access.table_lineage l JOIN o
  ON l.target_table_catalog=o.c AND l.target_table_schema=o.s AND l.target_table_name=o.t
WHERE l.event_date >= current_date()-365
GROUP BY 1"""
    q3_columns, q3_rows = run_sql(WAREHOUSE_ID, q3_sql)
    write_csv("q3_writers_365d.csv", q3_columns, q3_rows)

    writer_job_ids: set[str] = set()
    job_column_index: int = q3_columns.index("writer_job_ids")
    for row in q3_rows:
        writer_job_ids.update(job_id.strip() for job_id in (row[job_column_index] or "").split(",") if job_id.strip())
    if writer_job_ids:
        id_list = ",".join(f"'{job_id}'" for job_id in sorted(writer_job_ids))
        write_csv("q4_jobs.csv", *run_sql(WAREHOUSE_ID, f"""
SELECT job_id, name, run_as, run_as_user_name, creator_user_name, paused, delete_time, trigger_type
FROM system.lakeflow.jobs WHERE job_id IN ({id_list})
QUALIFY row_number() OVER (PARTITION BY job_id ORDER BY change_time DESC)=1"""))
        write_csv("q4_job_runs_30d.csv", *run_sql(WAREHOUSE_ID, f"""
SELECT job_id, count(*) runs_30d, sum(CASE WHEN result_state='SUCCEEDED' THEN 1 ELSE 0 END) ok_30d,
  max(period_start_time) last_run, max_by(result_state, period_start_time) last_state
FROM system.lakeflow.job_run_timeline
WHERE job_id IN ({id_list}) AND period_start_time >= current_date()-30 AND result_state IS NOT NULL
GROUP BY 1"""))

    # Q5a dashboards: every dashboard id seen reading these objects, resolved to name and dataset SQL.
    with open(os.path.join(FACTS_FOLDER, "q2_readers_90d.csv"), encoding="utf-8") as readers_file:
        dashboard_ids: set[str] = set()
        for row in csv.DictReader(readers_file):
            if row["read_via"].startswith("DASHBOARD"):
                dashboard_ids.update(i.strip() for i in row["entity_ids"].split(",") if i.strip())
    dashboards: list[dict] = []
    for dashboard_id in sorted(dashboard_ids):
        try:
            dashboard = call_api("GET", f"/api/2.0/lakeview/dashboards/{dashboard_id}")
            serialized = json.loads(dashboard.get("serialized_dashboard") or "{}")
            dataset_sql = [
                {"name": dataset.get("displayName") or dataset.get("name"),
                 "sql": "".join(dataset.get("queryLines") or [dataset.get("query", "")])}
                for dataset in serialized.get("datasets", [])]
            dashboards.append({"id": dashboard_id, "name": dashboard.get("display_name"),
                               "path": dashboard.get("path"), "state": dashboard.get("lifecycle_state"),
                               "warehouse_id": dashboard.get("warehouse_id"), "datasets": dataset_sql})
        except urllib.error.HTTPError as http_error:
            dashboards.append({"id": dashboard_id, "error": f"HTTP {http_error.code}: not readable"})
    with open(os.path.join(FACTS_FOLDER, "q5_dashboards.json"), "w", encoding="utf-8") as output_file:
        json.dump(dashboards, output_file, indent=2)
    print(f"q5_dashboards.json: {len(dashboards)} dashboards")

    # Q5b Genie: match on full names so nonprod and prod copies stay separate.
    genie_matches: list[dict] = []
    genie_errors: list[str] = []
    space_list: list[dict] = []
    page_token: str | None = None
    while True:
        try:
            page = call_api("GET", "/api/2.0/genie/spaces" + (f"?page_token={page_token}" if page_token else ""))
        except urllib.error.HTTPError as http_error:
            # The personal token gets 403 on the Genie list; record it so the gap is visible, not silent.
            genie_errors.append(f"space list: HTTP {http_error.code}")
            break
        space_list.extend(page.get("spaces", []))
        page_token = page.get("next_page_token")
        if not page_token:
            break
    for space in space_list:
        space_id = space.get("space_id")
        try:
            detail = call_api("GET", f"/api/2.0/genie/spaces/{space_id}?include_serialized_space=true")
            serialized_text = (detail.get("serialized_space") or "").lower()
        except urllib.error.HTTPError as http_error:
            genie_errors.append(f"{space_id} {space.get('title')}: HTTP {http_error.code}")
            continue
        for full_name in full_names:
            if full_name.lower() in serialized_text:
                genie_matches.append({"full_name": full_name, "space_id": space_id, "space_title": space.get("title")})
    with open(os.path.join(FACTS_FOLDER, "q5_genie.json"), "w", encoding="utf-8") as output_file:
        json.dump({"spaces_checked": len(space_list), "unreadable": genie_errors, "matches": genie_matches},
                  output_file, indent=2)
    print(f"q5_genie.json: {len(space_list)} spaces checked, {len(genie_errors)} unreadable, "
          f"{len(genie_matches)} matches")


if __name__ == "__main__":
    main()
