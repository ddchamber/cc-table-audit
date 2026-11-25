"""Step 5: merge verdicts/music.csv and verdicts/voc.csv, check completeness, and flag risky calls.

Checks:
  1. every object in objects.csv has exactly one row; no extras; allowed call values; no em or en dashes
  2. any Delete or Sandbox with a dashboard, Genie space, job write in 7 days, other reader in 30 days, or
     anything naming it (view, dashboard dataset, code that is not its own one-off build)
  3. any Promote to prod with no dashboard, no Genie space and no other reader
  4. blank targets on Keep as is get the current full name plus "(stays here)"
Writes out/dan_chamberlin_audit_fact_checked.csv and prints the flags.
"""
import csv
import datetime
import json
import os

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
ALLOWED_CALLS: set[str] = {"Keep as is", "Move to bronze", "Move to silver", "Move to gold", "Promote to prod",
                           "Delete", "Sandbox", "Retire after repointing", "Your decision"}
OUTPUT_COLUMNS: list[str] = ["sheet_row", "full_name", "my_call", "target", "vs_sachin", "why", "facts",
                             "confidence", "check_before_acting"]
TODAY: datetime.date = datetime.date(2026, 11, 18)


def main() -> None:
    with open(os.path.join(AUDIT_FOLDER, "objects.csv"), encoding="utf-8") as objects_file:
        expected = {row["full_name"]: int(row["sheet_row"]) for row in csv.DictReader(objects_file)}
    with open(os.path.join(AUDIT_FOLDER, "batches", "music.json"), encoding="utf-8") as music_file, \
         open(os.path.join(AUDIT_FOLDER, "batches", "voc.json"), encoding="utf-8") as voc_file:
        facts_by_name = {r["full_name"]: r for r in json.load(music_file) + json.load(voc_file)}

    verdict_rows: list[dict] = []
    for family in ("music", "voc"):
        with open(os.path.join(AUDIT_FOLDER, "verdicts", f"{family}.csv"), encoding="utf-8") as verdict_file:
            verdict_rows.extend(csv.DictReader(verdict_file))

    problems: list[str] = []
    seen: dict[str, int] = {}
    for row in verdict_rows:
        seen[row["full_name"]] = seen.get(row["full_name"], 0) + 1
        if row["my_call"] not in ALLOWED_CALLS:
            problems.append(f"{row['full_name']}: call not allowed: {row['my_call']!r}")
        if row["full_name"] in expected and str(expected[row["full_name"]]) != str(row["sheet_row"]).strip():
            problems.append(f"{row['full_name']}: sheet_row {row['sheet_row']} should be {expected[row['full_name']]}")
        for column_name in OUTPUT_COLUMNS:
            if "—" in (row.get(column_name) or "") or "–" in (row.get(column_name) or ""):
                problems.append(f"{row['full_name']}: dash character in {column_name}")
        if row["my_call"] == "Keep as is" and not (row.get("target") or "").strip():
            row["target"] = f"{row['full_name']} (stays here)"
    problems += [f"missing: {name}" for name in expected if name not in seen]
    problems += [f"extra: {name}" for name in seen if name not in expected]
    problems += [f"duplicate: {name} x{count}" for name, count in seen.items() if count > 1]

    risk_flags: list[str] = []
    for row in verdict_rows:
        facts = facts_by_name.get(row["full_name"])
        if not facts:
            continue
        last_write = (facts.get("writes_365d") or {}).get("last_write")
        recent_write = bool(last_write) and (TODAY - datetime.date.fromisoformat(str(last_write)[:10])).days <= 7
        last_other_read = facts.get("last_other_read")
        recent_reader = bool(last_other_read) and (TODAY - datetime.date.fromisoformat(str(last_other_read)[:10])).days <= 30
        if row["my_call"] in ("Delete", "Sandbox"):
            reasons = []
            if facts["dashboards"]: reasons.append("dashboard")
            if facts["genie_spaces"]: reasons.append("Genie")
            if recent_write: reasons.append(f"written {last_write}")
            if recent_reader: reasons.append(f"other reader {last_other_read}")
            if facts["named_by_views"]: reasons.append("named by a view")
            if facts["named_by_dashboard_datasets"]: reasons.append("named in dashboard SQL")
            if facts["named_by_workspace_code"]: reasons.append("named in workspace code")
            if reasons:
                risk_flags.append(f"{row['my_call']} {row['full_name']}: " + ", ".join(reasons))
        if row["my_call"] == "Promote to prod" and not (facts["dashboards"] or facts["genie_spaces"]
                                                        or facts["other_readers_90d"]):
            risk_flags.append(f"Promote {row['full_name']}: no dashboard, Genie or other reader")

    os.makedirs(os.path.join(AUDIT_FOLDER, "out"), exist_ok=True)
    verdict_rows.sort(key=lambda r: int(r["sheet_row"]))
    output_path = os.path.join(AUDIT_FOLDER, "out", "dan_chamberlin_audit_fact_checked.csv")
    with open(output_path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(verdict_rows)

    print(f"rows: {len(verdict_rows)} (expected {len(expected)})")
    print("problems:", problems or "none")
    print("risk flags:", *(risk_flags or ["none"]), sep="\n  ")


if __name__ == "__main__":
    main()
