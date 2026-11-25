"""Check verdicts/voc.csv: 41 rows, each batch object once, allowed calls, no em or en dashes, and print totals."""
import collections
import csv
import json

BATCH_PATH: str = r"C:\Users\dan.chamberlin\TM\table-audit\batches\voc.json"
VERDICT_PATH: str = r"C:\Users\dan.chamberlin\TM\table-audit\verdicts\voc.csv"
ALLOWED_CALLS: set[str] = {"Keep as is", "Move to bronze", "Move to silver", "Move to gold", "Promote to prod", "Delete", "Sandbox", "Retire after repointing", "Your decision"}

with open(BATCH_PATH, encoding="utf-8") as batch_file:
    batch_names: list[str] = [record["full_name"] for record in json.load(batch_file)]
with open(VERDICT_PATH, encoding="utf-8", newline="") as verdict_file:
    verdict_rows: list[dict[str, str]] = list(csv.DictReader(verdict_file))
with open(VERDICT_PATH, encoding="utf-8") as verdict_file:
    raw_text: str = verdict_file.read()

name_counts = collections.Counter(row["full_name"] for row in verdict_rows)
print("rows:", len(verdict_rows))
print("every batch name exactly once:", all(name_counts[name] == 1 for name in batch_names) and set(name_counts) == set(batch_names))
print("em or en dashes:", raw_text.count("\u2014") + raw_text.count("\u2013"))
print("bad calls:", [row["my_call"] for row in verdict_rows if row["my_call"] not in ALLOWED_CALLS])
print("blank target where required:", [row["sheet_row"] for row in verdict_rows if row["my_call"] not in ("Delete", "Retire after repointing", "Your decision") and not row["target"]])
print("by call:", dict(collections.Counter(row["my_call"] for row in verdict_rows)))
print("vs Sachin:", dict(collections.Counter(row["vs_sachin"] for row in verdict_rows)))
print("confidence:", dict(collections.Counter(row["confidence"] for row in verdict_rows)))
