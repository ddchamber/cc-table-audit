"""Step 11 (2026-11-23): pre-fill Dan's 'Your decision' (P) and 'Comment' (Q) from Claude's calls, at Dan's request.

Column P is a dropdown limited to Keep / Sandbox / Delete / Not sure ('How to read it' tab), so a move is
written as Keep with the destination in the comment. Medium-confidence rows get their open check in the comment.
Output: out/sheet_chunks/decision_prod.json (rows 7 to 77) and decision_nonprod.json (rows 88 to 111).
"""
import csv
import json
from pathlib import Path

audit_folder: Path = Path(__file__).parent
with open(audit_folder / "out" / "dan_chamberlin_audit_final.csv", encoding="utf-8") as verdict_file:
    verdicts_by_row: dict[int, dict] = {int(r["sheet_row"]): r for r in csv.DictReader(verdict_file)}

# Short checks for the 10 Medium rows, matching the summary tab wording.
MEDIUM_ROW_CHECKS: dict[str, str] = {
    "voc_account_id_mapping": "Ask Siritha Akula and Michael Wiederhold if they still query it.",
    "music_event_phase_summary_step22": "Ask Duygu Unaldi first; point her at music_event_phase_summary.",
    "voc_mapping_products": "Confirm product tagging will use it; if not, delete instead.",
    "voc_opportunity_id18_mapping": "Edit 07_gold_opportunity_id18_mapping.sql and tell Michael Wiederhold.",
    "music_event_phase_summary_step16_live": "Only older copy; confirm nobody needs the September numbers.",
    "music_queue_member_fact_step16_live": "Only older copy; confirm nobody needs the September numbers.",
    "music_asu_event_signups_step19_rollback": "Only older copy; confirm nobody needs the September numbers.",
    "music_str_daily_step16_live": "Only older copy; confirm nobody needs the September numbers.",
    "voc_mapping_competitors": "Ask Matthew Sutton if he will re-run his 07-30 notebook.",
    "voc_silver_wonloss_interviews": "Ask Matthew Sutton if he will re-run his 07-30 notebook.",
}


def decision_and_comment(row: dict) -> list[str]:
    table_name = row["full_name"].split(".")[-1]
    call = row["my_call"]
    if call == "Keep as is":
        decision, comment = "Keep", "Stays here."
    elif call == "Move to silver":
        decision = "Keep"
        comment = f"Move to {row['target']}."
        if table_name.startswith("music"):
            comment += " Ships with moving music-dashboard-nightly to the team service account."
        else:
            # Not every VOC mapping is named by the same views or the loader; column X lists each one's own.
            comment += " Update what names it first (column X)."
    elif call == "Delete":
        # Not 'nothing reads it': the step22 phase summary had one read on 11-10. Point at the reason instead.
        decision, comment = "Delete", "Reason in column U."
    else:
        raise ValueError(f"unexpected call {call} for {table_name}")
    if row["confidence"] == "Medium":
        comment += " Check first: " + MEDIUM_ROW_CHECKS[table_name]
    return [decision, comment]


for label, first_row, last_row in (("prod", 7, 77), ("nonprod", 88, 111)):
    values = [decision_and_comment(verdicts_by_row[r]) for r in range(first_row, last_row + 1)]
    payload = {"range": f"'Dan Chamberlin'!P{first_row}:Q{last_row}", "values": values}
    (audit_folder / "out" / "sheet_chunks" / f"decision_{label}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")

all_decisions = [decision_and_comment(r)[0] for r in verdicts_by_row.values()]
print({d: all_decisions.count(d) for d in set(all_decisions)})
