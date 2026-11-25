"""Step 10 (2026-11-23): build paste-ready values for columns R to X on the 'Dan Chamberlin' tab.

Layout copied from the 'Matthew Sutton' tab: band label in R of the band row, headers R to X in the
header row, then one row per object keyed by its sheet row number. Writes one JSON file per
contiguous block (prod rows 7 to 77, nonprod rows 88 to 111), split into chunks small enough for
one sheet call each. Read-only on everything except the local out/ folder.
"""
import csv
import json
from pathlib import Path

audit_folder: Path = Path(__file__).parent
output_folder: Path = audit_folder / "out" / "sheet_chunks"
output_folder.mkdir(exist_ok=True)

HEADER_ROW: list[str] = ["Claude's call", "Should live in (Claude)", "vs Sachin", "Why (plain English)",
                         "Facts it rests on", "Confidence", "Check before acting"]
BAND_LABEL: str = ("CLAUDE'S CHALLENGE  ·  fact-checked 2026-11-18, Music rechecked live 2026-11-23 "
                   "(Databricks lineage, jobs, dashboards, Genie, local project files, Obsidian)")
ROWS_PER_CHUNK: int = 18

with open(audit_folder / "out" / "dan_chamberlin_audit_final.csv", encoding="utf-8") as verdict_file:
    verdicts_by_row: dict[int, dict] = {int(r["sheet_row"]): r for r in csv.DictReader(verdict_file)}
assert len(verdicts_by_row) == 95


def sheet_values(row: dict) -> list[str]:
    # Matthew's tab shows the bare destination name; " (stays here)" was our own annotation.
    destination = row["target"].replace(" (stays here)", "")
    return [row["my_call"], destination, row["vs_sachin"], row["why"], row["facts"],
            row["confidence"], row["check_before_acting"]]


chunk_index: int = 0
for first_row, last_row in ((7, 77), (88, 111)):
    block_rows = list(range(first_row, last_row + 1))
    assert all(r in verdicts_by_row for r in block_rows), f"gap in rows {first_row} to {last_row}"
    for start in range(0, len(block_rows), ROWS_PER_CHUNK):
        chunk_rows = block_rows[start:start + ROWS_PER_CHUNK]
        chunk = {"range": f"'Dan Chamberlin'!R{chunk_rows[0]}:X{chunk_rows[-1]}",
                 "values": [sheet_values(verdicts_by_row[r]) for r in chunk_rows]}
        chunk_index += 1
        chunk_path = output_folder / f"chunk_{chunk_index:02d}.json"
        chunk_path.write_text(json.dumps(chunk, ensure_ascii=False), encoding="utf-8")
        print(chunk_path.name, chunk["range"], len(chunk_path.read_text(encoding="utf-8")), "chars")

(output_folder / "headers.json").write_text(json.dumps({
    "prod": {"band": "'Dan Chamberlin'!R5", "header": "'Dan Chamberlin'!R6:X6"},
    "nonprod": {"band": "'Dan Chamberlin'!R86", "header": "'Dan Chamberlin'!R87:X87"},
    "band_label": BAND_LABEL, "header_row": HEADER_ROW}, ensure_ascii=False), encoding="utf-8")
