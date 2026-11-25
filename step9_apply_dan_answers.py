"""Step 9 (2026-11-23): apply Dan's answers to the fact-checked verdicts and write the final file.

Dan's answers:
  - music_missing_revenue_events: not meant for readers, so Move to silver with its _nightly copy (11-18).
  - the 24 nonprod VOC copies: Delete (11-23, after the live recheck showed one write on 07-22 and no reads).
Input:  out/dan_chamberlin_audit_fact_checked.csv (95 rows)
Output: out/dan_chamberlin_audit_final.csv (95 rows), checked for row count and no dashes.
"""
import csv
from pathlib import Path

audit_folder: Path = Path(__file__).parent
input_path: Path = audit_folder / "out" / "dan_chamberlin_audit_fact_checked.csv"
output_path: Path = audit_folder / "out" / "dan_chamberlin_audit_final.csv"

with open(input_path, encoding="utf-8") as input_file:
    reader = csv.DictReader(input_file)
    column_names: list[str] = list(reader.fieldnames or [])
    verdict_rows: list[dict[str, str]] = list(reader)

changed_rows: int = 0
for row in verdict_rows:
    full_name: str = row["full_name"]
    table_name: str = full_name.split(".")[-1]

    if full_name == "prod_shared_gold.central_analytics_crd.music_missing_revenue_events":
        row["my_call"] = "Move to silver"
        row["target"] = "prod_shared_silver.central_analytics_enr.music_missing_revenue_events"
        row["why"] = ("List of shows with tickets sold but no revenue, which the show rule drops from the cards. "
                      "Dan confirmed it is not meant for readers: it is built by 06_missing_revenue_events.sql and "
                      "checked by the gate, and no dashboard, Genie space or other person reads it. That makes it a "
                      "pipeline building block, so it moves to silver with its _nightly copy.")
        row["confidence"] = "High"
        row["check_before_acting"] = (
            "Ships with the job move: music-dashboard-nightly runs as Dan, who cannot write prod silver, so the job "
            "must run as sp_prod_tm_central_analytics. Change the name in the generator and regenerate the "
            "music_nightly files (06_missing_revenue_events.sql, 10_gate.sql, 99_publish.sql), and update the "
            "Confluence pipeline table page. Delete the old gold copy after the first green run.")
        changed_rows += 1

    elif full_name.startswith("nonprod_shared_gold.") and table_name.startswith("voc"):
        owner_note = (" Owner confirmed Delete on 11-23: every nonprod VOC copy was written once on 07-22 and never "
                      "again, while the interview loader refreshes the prod tables.")
        if "Owner confirmed" not in row["why"]:
            row["why"] = row["why"].rstrip() + owner_note
            changed_rows += 1

    # Live recheck 2026-11-23: the dashboard edit of 11-20 stopped reading these two directly
    # (it now reads music_asu_tour_conversion_by_tour). People and the nightly job still read them.
    if table_name == "music_asu_tour_conversion":
        row["why"] = ("Artist Sign Up conversion per campaign group, published by the nightly job. Since the 11-20 "
                      "dashboard edit the dashboard reads the new music_asu_tour_conversion_by_tour instead, but "
                      "people still read this one directly (Sean Poole's job, Matthew Sutton and others in the "
                      "last 7 days) and the nightly job reads it, so it stays in gold.")
        changed_rows += 1
    if table_name == "music_asu_event_signups":
        row["why"] = ("Artist Sign Up sign-ups per event, published by the nightly job. Since the 11-20 dashboard "
                      "edit the dashboard no longer reads it directly, but Sean Poole read it in the last 7 days "
                      "and the nightly job builds the benchmark and conversion tables from it, so it stays in gold.")
        changed_rows += 1
    if table_name in ("music_asu_tour_conversion", "music_asu_event_signups"):
        row["facts"] = row["facts"].replace("Dashboard: TM Music", "Dashboard (until its 11-20 edit): TM Music")
        row["facts"] = row["facts"].replace("Genie: TM Music", "Genie (until 11-20): TM Music")

# Self-checks: same rows in, same rows out, and no dashes (house style for the sheet text).
assert len(verdict_rows) == 95, f"expected 95 rows, got {len(verdict_rows)}"
assert len({r["full_name"] for r in verdict_rows}) == 95, "duplicate objects"
for row in verdict_rows:
    for column_name in ("why", "check_before_acting"):
        assert "—" not in row[column_name] and "–" not in row[column_name], (row["full_name"], column_name)

with open(output_path, "w", newline="", encoding="utf-8") as output_file:
    writer = csv.DictWriter(output_file, fieldnames=column_names)
    writer.writeheader()
    writer.writerows(verdict_rows)

from collections import Counter
print(f"changed {changed_rows} rows -> {output_path.name}")
print("calls:", Counter(r["my_call"] for r in verdict_rows))
print("vs Sachin:", Counter(r["vs_sachin"] for r in verdict_rows))
print("confidence:", Counter(r["confidence"] for r in verdict_rows))
