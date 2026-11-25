"""Step 4 prep: split the evidence pack plus the breakage facts into two review batches (Music, VOC)."""
import json
import os

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))


def compact_record(evidence: dict, breakage: dict) -> dict:
    """Keep what a reviewer needs; drop the per-reader detail rows except the non-owner ones."""
    readers = evidence["readers_90d"]
    return {
        "sheet_row": evidence["sheet_row"],
        "full_name": evidence["full_name"],
        "sachin": evidence["sachin"],
        "metadata": evidence["metadata"],
        "other_readers_90d": readers["other_people"],
        "last_other_read": readers["last_other_read"],
        "other_reader_detail": [d for d in readers["detail"] if d["reader_class"] == "other_person"],
        "owner_read_days_90d": readers["owner_read_days"],
        "sachin_crawl_dates": readers["sachin_crawl_dates"],
        "service_principal_readers": readers["service_principals"],
        "dashboards": evidence["dashboards"],
        "genie_spaces": evidence["genie_spaces"],
        "reading_jobs": evidence["reading_jobs"],
        "writes_365d": evidence["writes_365d"],
        "writer_jobs": evidence["writer_jobs"],
        "named_by_views": breakage["views"],
        "named_by_dashboard_datasets": sorted({d["where"] for d in breakage["dashboard_datasets"]}),
        "named_by_workspace_code": breakage["workspace_code"],
        "tables_built_from_it_365d": [b for b in breakage["built_tables_365d"] if not b["built_table"].startswith("__")],
        "local_files": evidence["local_files"],
    }


def main() -> None:
    with open(os.path.join(AUDIT_FOLDER, "evidence_pack.json"), encoding="utf-8") as input_file:
        evidence_objects = json.load(input_file)["objects"]
    with open(os.path.join(AUDIT_FOLDER, "facts", "breakage.json"), encoding="utf-8") as input_file:
        breakage_by_name = {o["full_name"]: o for o in json.load(input_file)["objects"]}
    os.makedirs(os.path.join(AUDIT_FOLDER, "batches"), exist_ok=True)
    os.makedirs(os.path.join(AUDIT_FOLDER, "verdicts"), exist_ok=True)
    for family in ("music", "voc"):
        batch = [compact_record(e, breakage_by_name[e["full_name"]]) for e in evidence_objects
                 if e["full_name"].split(".")[-1].startswith(family + "_")]
        with open(os.path.join(AUDIT_FOLDER, "batches", f"{family}.json"), "w", encoding="utf-8") as output_file:
            json.dump(batch, output_file, indent=2, default=str)
        print(f"batches/{family}.json: {len(batch)} objects")


if __name__ == "__main__":
    main()
