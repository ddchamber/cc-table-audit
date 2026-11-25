"""Turn facts/breakage.json into breakage.md: per object, what names it and what must change before it moves."""
import json
import os

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
SHORT_SCHEMA: str = "_shared_gold.central_analytics_crd"
DAN_NIGHTLY_JOB_ID: str = "489488962317323"


def shorten(full_name: str) -> str:
    return full_name.replace(SHORT_SCHEMA, "")


def describe(record: dict) -> tuple[list[str], list[str]]:
    """Return (what names it, what must change before a move or delete)."""
    named_by: list[str] = []
    must_change: list[str] = []
    for view in record["views"]:
        label = "metric view" if view["kind"] == "METRIC_VIEW" else "view"
        named_by.append(f"{label} `{shorten(view['where'])}` ({(view.get('owner') or '').split('@')[0]})")
        must_change.append(f"repoint the {label} `{shorten(view['where'])}`")
    dashboards = sorted({d["where"].split(" / ")[0] for d in record["dashboard_datasets"]})
    for dashboard_name in dashboards:
        dataset_count = sum(d["where"].startswith(dashboard_name + " / ") for d in record["dashboard_datasets"])
        named_by.append(f"dashboard \"{dashboard_name}\" ({dataset_count} datasets)")
        must_change.append(f"edit {dataset_count} dataset queries in \"{dashboard_name}\"")
    if record["dashboard_internal_views"]:
        named_by.append(f"{record['dashboard_internal_views']} internal Genie views of that dashboard (follow the dashboard)")
    for space in record["genie_spaces"]:
        named_by.append(f"Genie space \"{space}\"")
        must_change.append(f"swap the table in Genie space \"{space}\"")
    writing_files = sorted({c["where"].split("/")[-1] for c in record["workspace_code"] if c["writes_it"]})
    reading_files = sorted({c["where"].split("/")[-1] for c in record["workspace_code"] if not c["writes_it"]
                            and c["where"].split("/")[-1] not in writing_files})
    if writing_files:
        named_by.append("written by " + ", ".join(f"`{f}`" for f in writing_files))
        must_change.append("change the target in " + ", ".join(f"`{f}`" for f in writing_files))
    if reading_files:
        named_by.append("read by " + ", ".join(f"`{f}`" for f in reading_files))
        code_files = [f for f in reading_files if f.endswith(".sql")]
        if code_files:
            must_change.append("update the name in " + ", ".join(f"`{f}`" for f in code_files))
    for job in record["reading_jobs"]:
        # Dan's nightly job is the music_nightly SQL files already listed above; only flag others' jobs.
        if job["job_id"] == DAN_NIGHTLY_JOB_ID:
            continue
        named_by.append(f"read by job \"{job.get('name') or job['job_id']}\"")
        must_change.append(f"tell the owner of job \"{job.get('name') or job['job_id']}\" (code not visible to Dan)")
    other_owner_builds = [b for b in record["built_tables_365d"]
                          if "dan.chamberlin" not in b["built_by"] and not b["built_table"].startswith("__")]
    for build in other_owner_builds:
        named_by.append(f"`{shorten(build['built_table'])}` was built from it on {build['last_build']} "
                        f"({build['built_by'].split('@')[0]})")
        must_change.append(f"check with {build['built_by'].split('@')[0]} before moving (their rebuild reads it)")
    return named_by, must_change


def main() -> None:
    with open(os.path.join(AUDIT_FOLDER, "facts", "breakage.json"), encoding="utf-8") as input_file:
        breakage = json.load(input_file)

    lines: list[str] = [
        "# Breakage check: what must change before each object moves or is deleted",
        "",
        "Built 2026-11-18 from `facts/breakage.json`. Read-only; nothing in Databricks was changed.",
        "",
        "Sources searched: stored SQL of every view in the metastore; every metric view definition Dan can read "
        f"({breakage['metric_views_scanned'] - len(breakage['metric_view_errors'])} of {breakage['metric_views_scanned']}; "
        "the rest are 403, other teams' views); dataset SQL of every dashboard that read one of these objects in "
        f"365 days ({len(breakage['dashboard_errors'])} deleted dashboards skipped); all "
        f"{breakage['workspace_files_scanned']} files in Dan's workspace folder, including the `music_nightly` job; "
        "Genie spaces Dan can see; jobs that read them; tables built from them in 365 days by someone other than Dan.",
        "",
        "Gaps: Shaan's `CI-Bot` job code is not visible to Dan. The 299 unreadable metric views would still show in "
        "lineage if anyone queried them.",
        "",
        "| Row | Object | Sachin's call | Where Sachin puts it | Named by | Must change first |",
        "|---|---|---|---|---|---|",
    ]
    clear_count = 0
    for record in breakage["objects"]:
        named_by, must_change = describe(record)
        if not named_by:
            clear_count += 1
        lines.append("| {} | `{}` | {} | {} | {} | {} |".format(
            record["sheet_row"], shorten(record["full_name"]), record["sachin_call"],
            record["sachin_live_in"] or "", "; ".join(named_by) or "nothing",
            "; ".join(must_change) or "nothing: safe to move or delete as is"))
    lines.insert(8, f"Objects with nothing pointing at them: {clear_count} of {len(breakage['objects'])}.")
    lines.insert(9, "")
    with open(os.path.join(AUDIT_FOLDER, "breakage.md"), "w", encoding="utf-8") as output_file:
        output_file.write("\n".join(lines) + "\n")
    print(f"breakage.md written; {clear_count} objects have nothing pointing at them")


if __name__ == "__main__":
    main()
