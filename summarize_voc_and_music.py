"""Summarize the VOC verdicts and the Music verdicts for the 2026-11-23 talk-through with Dan.

Read-only: prints counts and short rows from the fact-checked verdict file.
"""
import csv
from collections import Counter
from pathlib import Path

audit_folder: Path = Path(__file__).parent
verdict_rows: list[dict[str, str]] = list(
    csv.DictReader(open(audit_folder / "out" / "dan_chamberlin_audit_fact_checked.csv", encoding="utf-8"))
)

def environment_of(full_name: str) -> str:
    return full_name.split("_shared_")[0]

for family in ("voc", "music"):
    family_rows = [r for r in verdict_rows if r["full_name"].split(".")[-1].startswith(family)]
    print(f"===== {family.upper()} ({len(family_rows)} objects)")
    print(Counter((environment_of(r["full_name"]), r["my_call"]) for r in family_rows))
    for row in family_rows:
        table_name = row["full_name"].split(".")[-1]
        print(f"  row {row['sheet_row']:>3} | {environment_of(row['full_name']):7} | {row['my_call']:15} | "
              f"{row['vs_sachin']:13} | {table_name}")
    print()
