"""Step 2d: join Sachin's columns, Q1 to Q5 and local files into evidence_pack.json (one record per object).

Sachin's columns come from the downloaded .xlsx; this script checks that each row's table name and
suggested call match the row numbers in objects.csv, so a stale export cannot slip in.
Readers are split into: other people, the owner (Dan), Sachin's inventory crawl, and service principals.
"""
import csv
import json
import os
import re
from collections import defaultdict

import openpyxl

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
FACTS_FOLDER: str = os.path.join(AUDIT_FOLDER, "facts")
SHEET_EXPORT_PATH: str = r"C:\Users\dan.chamberlin\Downloads\Central Analytics schema cleanup review 2026-11-16.xlsx"
OWNER_USER: str = "dan.chamberlin@ticketmaster.com"
SACHIN_USER: str = "sachin.dewangan@ticketmaster.com"
SERVICE_PRINCIPAL_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SACHIN_COLUMN_HEADERS: list[str] = [
    "readers_7d", "readers_15d", "readers_30d", "readers_90d", "who_used_it", "created", "last_refreshed",
    "by_a_job", "size_gb", "should_live_in", "suggested_call", "why"]


def read_csv(file_name: str) -> list[dict]:
    with open(os.path.join(FACTS_FOLDER, file_name), encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))


def classify_reader(reader: str) -> str:
    if reader == OWNER_USER:
        return "owner"
    if reader == SACHIN_USER:
        return "sachin_crawl"
    if SERVICE_PRINCIPAL_PATTERN.match(reader):
        return "service_principal"
    return "other_person"


def main() -> None:
    with open(os.path.join(AUDIT_FOLDER, "objects.csv"), encoding="utf-8") as objects_file:
        objects: list[dict] = list(csv.DictReader(objects_file))

    worksheet = openpyxl.load_workbook(SHEET_EXPORT_PATH, read_only=True, data_only=True)["Dan Chamberlin"]
    sheet_rows: dict[int, list] = {index: list(row) for index, row in enumerate(worksheet.iter_rows(values_only=True), 1)}

    metadata_by_name = {row["full_name"]: row for row in read_csv("q1_metadata.csv")}
    writers_by_name = {row["full_name"]: row for row in read_csv("q3_writers_365d.csv")}
    readers_by_name: dict[str, list[dict]] = defaultdict(list)
    for row in read_csv("q2_readers_90d.csv"):
        row["reader_class"] = classify_reader(row["reader"])
        readers_by_name[row["full_name"]].append(row)
    jobs_by_id = {row["job_id"]: row for row in read_csv("q4_jobs.csv")}
    runs_by_id = {row["job_id"]: row for row in read_csv("q4_job_runs_30d.csv")}
    with open(os.path.join(FACTS_FOLDER, "q5_dashboards.json"), encoding="utf-8") as input_file:
        dashboards_by_id = {d["id"]: d for d in json.load(input_file)}
    with open(os.path.join(FACTS_FOLDER, "q5_genie.json"), encoding="utf-8") as input_file:
        genie = json.load(input_file)
    genie_by_name: dict[str, list[str]] = defaultdict(list)
    for match in genie["matches"]:
        genie_by_name[match["full_name"]].append(match["space_title"])
    with open(os.path.join(FACTS_FOLDER, "local_files.json"), encoding="utf-8") as input_file:
        local_files = json.load(input_file)["by_object"]

    mismatches: list[str] = []
    evidence_pack: list[dict] = []
    for tab_object in objects:
        full_name = tab_object["full_name"]
        bare_name = full_name.split(".")[-1]
        sheet_row_number = int(tab_object["sheet_row"])
        exported_row = sheet_rows.get(sheet_row_number, [])
        if not exported_row or exported_row[0] != bare_name:
            mismatches.append(f"row {sheet_row_number}: export has {exported_row[:1]}, expected {bare_name}")
        sachin_columns = dict(zip(SACHIN_COLUMN_HEADERS, exported_row[3:15]))

        reader_rows = readers_by_name.get(full_name, [])
        other_people = sorted({r["reader"].split("@")[0] for r in reader_rows if r["reader_class"] == "other_person"})
        last_other_read = max((r["last_read"] for r in reader_rows if r["reader_class"] == "other_person"), default=None)
        dashboard_ids = sorted({i.strip() for r in reader_rows if r["read_via"].startswith("DASHBOARD")
                                for i in r["entity_ids"].split(",") if i.strip()})
        reading_job_ids = sorted({i.strip() for r in reader_rows if r["read_via"] == "JOB"
                                  for i in r["entity_ids"].split(",") if i.strip()})
        writer = writers_by_name.get(full_name, {})
        writer_job_ids = [i.strip() for i in (writer.get("writer_job_ids") or "").split(",") if i.strip()]

        evidence_pack.append({
            "sheet_row": sheet_row_number,
            "full_name": full_name,
            "sachin": sachin_columns,
            "metadata": metadata_by_name.get(full_name),
            "readers_90d": {
                "other_people": other_people,
                "other_people_count": len(other_people),
                "last_other_read": last_other_read,
                "owner_read_days": sum(int(r["read_days"]) for r in reader_rows if r["reader_class"] == "owner"),
                "sachin_crawl_dates": sorted({d for r in reader_rows if r["reader_class"] == "sachin_crawl"
                                              for d in r["read_dates"].split(", ")}),
                "service_principals": sorted({r["reader"] for r in reader_rows if r["reader_class"] == "service_principal"}),
                "feeds_tables": sorted({t for r in reader_rows for t in r["feeds_tables"].split(", ") if t}),
                "detail": reader_rows,
            },
            "dashboards": [{"id": i, "name": dashboards_by_id.get(i, {}).get("name"),
                            "path": dashboards_by_id.get(i, {}).get("path")} for i in dashboard_ids],
            "reading_jobs": [{"job_id": i, "name": jobs_by_id.get(i, {}).get("name")} for i in reading_job_ids],
            "genie_spaces": genie_by_name.get(full_name, []),
            "writes_365d": writer or None,
            "writer_jobs": [{**jobs_by_id.get(i, {"job_id": i}), "runs_30d": runs_by_id.get(i)} for i in writer_job_ids],
            "local_files": local_files.get(bare_name, {}),
        })

    with open(os.path.join(AUDIT_FOLDER, "evidence_pack.json"), "w", encoding="utf-8") as output_file:
        json.dump({"genie_spaces_checked": genie["spaces_checked"], "genie_unreadable": genie["unreadable"],
                   "objects": evidence_pack}, output_file, indent=2, default=str)
    print(f"evidence_pack.json: {len(evidence_pack)} objects; export row mismatches: {mismatches or 'none'}")


if __name__ == "__main__":
    main()
