"""Step 3: breakage check. For every object, list everything that names it, so we know what must
change before it moves or is deleted. Read-only.

Sources:
  a. views and materialized views anywhere in the metastore (stored SQL; lineage can miss these)
  b. dashboard dataset SQL for every dashboard that read any object in the last 365 days
  c. Dan's workspace code: every SQL file and notebook under /Users/dan.chamberlin@ticketmaster.com
     (this includes the music_nightly job files)
  d. Genie spaces (from step 2b) and jobs that read the object (lineage, from step 2)
Output: facts/breakage.json (per object) and breakage.md (what must change before this moves).
"""
import base64
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import call_api, run_sql

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
FACTS_FOLDER: str = os.path.join(AUDIT_FOLDER, "facts")
WAREHOUSE_ID: str = "dbb3244d6fa2f0fc"
DAN_WORKSPACE_ROOT: str = "/Users/dan.chamberlin@ticketmaster.com"


def load_objects() -> list[dict]:
    with open(os.path.join(AUDIT_FOLDER, "objects.csv"), encoding="utf-8") as objects_file:
        return list(csv.DictReader(objects_file))


def find_mentions(text: str, name_pattern: re.Pattern) -> set[str]:
    return {match.group(1).lower() for match in name_pattern.finditer(text or "")}


def list_workspace_files(root_path: str) -> list[dict]:
    """Walk the workspace tree; keep notebooks and files (SQL, Python) and skip repos' .git trees."""
    pending_folders: list[str] = [root_path]
    found_items: list[dict] = []
    while pending_folders:
        folder = pending_folders.pop()
        try:
            listing = call_api("GET", "/api/2.0/workspace/list?path=" + urllib.parse.quote(folder))
        except urllib.error.HTTPError:
            continue
        for item in listing.get("objects", []):
            if item["object_type"] in ("DIRECTORY", "REPO") and not item["path"].endswith("/.git"):
                pending_folders.append(item["path"])
            elif item["object_type"] in ("NOTEBOOK", "FILE"):
                found_items.append(item)
    return found_items


def export_source(workspace_path: str) -> str:
    exported = call_api("GET", "/api/2.0/workspace/export?format=SOURCE&path=" + urllib.parse.quote(workspace_path))
    return base64.b64decode(exported.get("content", "")).decode("utf-8", errors="ignore")


def main() -> None:
    objects = load_objects()
    bare_names: set[str] = {o["full_name"].split(".")[-1].lower() for o in objects}
    # '_' is a word character, so music_str_daily does not match inside music_str_daily_nightly.
    name_pattern = re.compile(r"\b(" + "|".join(sorted(map(re.escape, bare_names), key=len, reverse=True)) + r")\b",
                              re.IGNORECASE)
    mentions: dict[str, list[dict]] = defaultdict(list)

    # a. Views and materialized views whose stored SQL names an object.
    regex_alternation = "|".join(sorted(bare_names, key=len, reverse=True))
    view_columns, view_rows = run_sql(WAREHOUSE_ID, f"""
        SELECT v.table_catalog, v.table_schema, v.table_name, t.table_type, t.table_owner, v.view_definition
        FROM system.information_schema.views v
        LEFT JOIN system.information_schema.tables t
          ON t.table_catalog=v.table_catalog AND t.table_schema=v.table_schema AND t.table_name=v.table_name
        WHERE lower(v.view_definition) RLIKE '(^|[^a-z0-9_])({regex_alternation})([^a-z0-9_]|$)'""")
    for row in view_rows:
        view = dict(zip(view_columns, row))
        view_full_name = f"{view['table_catalog']}.{view['table_schema']}.{view['table_name']}"
        for referenced_name in find_mentions(view["view_definition"], name_pattern):
            # Keep the catalog the view points at, so prod and nonprod copies stay separate.
            qualified = re.findall(rf"([a-z0-9_`]+)\.[a-z0-9_`]+\.`?{referenced_name}\b", view["view_definition"].lower())
            mentions[referenced_name].append({
                "kind": view["table_type"] or "VIEW", "where": view_full_name, "owner": view["table_owner"],
                "catalogs_referenced": sorted({c.strip("`") for c in qualified}) or ["unqualified"]})
    print(f"a. views naming an object: {len(view_rows)}")

    # a2. Metric views keep their source in YAML, which information_schema.views does not search;
    # read each definition through the Unity Catalog API instead.
    _, metric_view_rows = run_sql(WAREHOUSE_ID, """
        SELECT table_catalog, table_schema, table_name, table_owner FROM system.information_schema.tables
        WHERE table_type = 'METRIC_VIEW'""")
    metric_view_errors: list[str] = []
    for catalog_name, schema_name, view_name, view_owner in metric_view_rows:
        metric_view_full_name = f"{catalog_name}.{schema_name}.{view_name}"
        try:
            definition = call_api("GET", "/api/2.1/unity-catalog/tables/" + urllib.parse.quote(metric_view_full_name))
        except urllib.error.HTTPError as http_error:
            metric_view_errors.append(f"{metric_view_full_name}: HTTP {http_error.code}")
            continue
        definition_text = definition.get("view_definition") or ""
        for referenced_name in find_mentions(definition_text, name_pattern):
            qualified = re.findall(rf"([a-z0-9_`]+)\.[a-z0-9_`]+\.`?{referenced_name}\b", definition_text.lower())
            mentions[referenced_name].append({
                "kind": "METRIC_VIEW", "where": metric_view_full_name, "owner": view_owner,
                "catalogs_referenced": sorted({c.strip("`") for c in qualified}) or ["unqualified"]})
    print(f"a2. metric views scanned: {len(metric_view_rows)} ({len(metric_view_errors)} unreadable)")

    # b. Dashboards that read any object in the last 365 days, scanned through their dataset SQL.
    values_list = ",".join("('{}','{}','{}')".format(*o["full_name"].split(".")) for o in objects)
    _, dashboard_rows = run_sql(WAREHOUSE_ID, f"""
        WITH o(c,s,t) AS (VALUES {values_list})
        SELECT DISTINCT l.entity_id FROM system.access.table_lineage l JOIN o
          ON l.source_table_catalog=o.c AND l.source_table_schema=o.s AND l.source_table_name=o.t
        WHERE l.event_date >= current_date()-365 AND l.entity_type LIKE 'DASHBOARD%'""")
    dashboard_errors: list[str] = []
    for (dashboard_id,) in dashboard_rows:
        try:
            dashboard = call_api("GET", f"/api/2.0/lakeview/dashboards/{dashboard_id}")
        except urllib.error.HTTPError as http_error:
            dashboard_errors.append(f"{dashboard_id}: HTTP {http_error.code}")
            continue
        serialized = json.loads(dashboard.get("serialized_dashboard") or "{}")
        for dataset in serialized.get("datasets", []):
            dataset_sql = "".join(dataset.get("queryLines") or [dataset.get("query", "")])
            for referenced_name in find_mentions(dataset_sql, name_pattern):
                qualified = re.findall(rf"([a-z0-9_`]+)\.[a-z0-9_`]+\.`?{referenced_name}\b", dataset_sql.lower())
                mentions[referenced_name].append({
                    "kind": "DASHBOARD_DATASET",
                    "where": f"{dashboard.get('display_name')} / {dataset.get('displayName') or dataset.get('name')}",
                    "owner": dashboard.get("path", "").split("/")[2] if dashboard.get("path") else None,
                    "lifecycle": dashboard.get("lifecycle_state"),
                    "catalogs_referenced": sorted({c.strip("`") for c in qualified}) or ["unqualified"]})
    print(f"b. dashboards scanned: {len(dashboard_rows)} ({len(dashboard_errors)} unreadable)")

    # c. Dan's workspace code, including the nightly job's SQL files.
    workspace_items = list_workspace_files(DAN_WORKSPACE_ROOT)
    export_errors: list[str] = []
    for item in workspace_items:
        try:
            source_text = export_source(item["path"])
        except urllib.error.HTTPError as http_error:
            export_errors.append(f"{item['path']}: HTTP {http_error.code}")
            continue
        for referenced_name in find_mentions(source_text, name_pattern):
            # Writes need the code changed before a move; reads only need the name updated.
            # A write only when the name is the target: directly after the write keyword, optionally
            # qualified as catalog.schema. (or in ${...} variables), not anywhere later in the statement.
            write_pattern = (rf"(create\s+(or\s+replace\s+)?(table|view)(\s+if\s+not\s+exists)?|insert\s+(overwrite|into)"
                             rf"(\s+table)?|merge\s+into|replace\s+table)\s+(identifier\()?['\"`]?([\w${{}}`.-]+\.)?"
                             rf"`?{referenced_name}\b")
            qualified = re.findall(rf"([a-z0-9_`]+)\.[a-z0-9_`]+\.`?{referenced_name}\b", source_text.lower())
            mentions[referenced_name].append({
                "kind": "WORKSPACE_" + item["object_type"], "where": item["path"],
                "writes_it": bool(re.search(write_pattern, source_text, re.IGNORECASE | re.DOTALL)),
                "in_nightly_job": "/music_nightly/" in item["path"],
                "catalogs_referenced": sorted({c.strip("`") for c in qualified}) or ["unqualified"]})
    print(f"c. workspace files scanned: {len(workspace_items)} ({len(export_errors)} unreadable)")

    # d. Genie spaces and reading jobs from step 2, carried over per full name.
    with open(os.path.join(AUDIT_FOLDER, "evidence_pack.json"), encoding="utf-8") as input_file:
        evidence_by_name = {o["full_name"]: o for o in json.load(input_file)["objects"]}

    # e. Tables built from each object in the last 365 days (step 2's reader window was only 90 days).
    built_columns, built_rows = run_sql(WAREHOUSE_ID, f"""
        WITH o(c,s,t) AS (VALUES {values_list})
        SELECT l.source_table_full_name full_name, l.target_table_full_name built_table,
               max(l.event_date) last_build, concat_ws(', ', collect_set(l.created_by)) built_by
        FROM system.access.table_lineage l JOIN o
          ON l.source_table_catalog=o.c AND l.source_table_schema=o.s AND l.source_table_name=o.t
        WHERE l.event_date >= current_date()-365 AND l.target_table_full_name IS NOT NULL
          AND l.target_table_full_name <> l.source_table_full_name
        GROUP BY 1, 2""")
    built_from_object: dict[str, list[dict]] = defaultdict(list)
    for row in built_rows:
        built = dict(zip(built_columns, row))
        built_from_object[built["full_name"]].append(built)
    print(f"e. downstream builds (365 days): {len(built_rows)}")

    breakage: list[dict] = []
    for tab_object in objects:
        full_name = tab_object["full_name"]
        catalog, _, bare_name = full_name.split(".")
        # A mention counts against this object only if it points at this catalog (or is unqualified).
        object_mentions = [m for m in mentions.get(bare_name.lower(), [])
                           if catalog in m["catalogs_referenced"] or "unqualified" in m["catalogs_referenced"]]
        evidence = evidence_by_name[full_name]
        breakage.append({
            "sheet_row": int(tab_object["sheet_row"]), "full_name": full_name,
            "sachin_call": evidence["sachin"]["suggested_call"], "sachin_live_in": evidence["sachin"]["should_live_in"],
            # Lakeview's internal 'lakegenie_' views belong to a dashboard's Genie and follow that dashboard.
            "views": [m for m in object_mentions if "VIEW" in m["kind"]
                      and not m["where"].startswith("__databricks_internal")],
            "dashboard_internal_views": len([m for m in object_mentions if m["where"].startswith("__databricks_internal")]),
            "built_tables_365d": built_from_object.get(full_name, []),
            "dashboard_datasets": [m for m in object_mentions if m["kind"] == "DASHBOARD_DATASET"],
            "workspace_code": [m for m in object_mentions if m["kind"].startswith("WORKSPACE_")],
            "genie_spaces": evidence["genie_spaces"],
            "reading_jobs": evidence["reading_jobs"],
        })

    with open(os.path.join(FACTS_FOLDER, "breakage.json"), "w", encoding="utf-8") as output_file:
        json.dump({"dashboard_errors": dashboard_errors, "export_errors": export_errors,
                   "metric_view_errors": metric_view_errors, "metric_views_scanned": len(metric_view_rows),
                   "workspace_files_scanned": len(workspace_items), "objects": breakage},
                  output_file, indent=2, default=str)
    print("facts/breakage.json written")


if __name__ == "__main__":
    main()
