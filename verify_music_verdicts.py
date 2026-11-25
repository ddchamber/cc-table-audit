"""Independent check of verdicts/music.csv against the batch: row count, names, dashes, tallies."""
import csv
import json
from collections import Counter
from pathlib import Path

AUDIT_FOLDER: Path = Path(r"C:\Users\dan.chamberlin\TM\table-audit")
batch_names: list[str] = [record["full_name"] for record in json.loads((AUDIT_FOLDER / "batches" / "music.json").read_text(encoding="utf-8"))]
raw_text: str = (AUDIT_FOLDER / "verdicts" / "music.csv").read_text(encoding="utf-8")
with (AUDIT_FOLDER / "verdicts" / "music.csv").open(encoding="utf-8", newline="") as input_file:
    rows: list[dict] = list(csv.DictReader(input_file))

csv_names: list[str] = [row["full_name"] for row in rows]
print("rows:", len(rows))
print("names match batch exactly once:", Counter(csv_names) == Counter(batch_names) and len(set(csv_names)) == len(csv_names))
print("em or en dashes:", raw_text.count("\u2014") + raw_text.count("\u2013"))
print("columns:", list(rows[0].keys()))
allowed_calls: set[str] = {"Keep as is", "Move to bronze", "Move to silver", "Move to gold", "Promote to prod", "Delete", "Sandbox", "Retire after repointing", "Your decision"}
print("bad calls:", [row["full_name"] for row in rows if row["my_call"] not in allowed_calls])
print("blank target where required:", [row["full_name"] for row in rows if row["my_call"] in ("Keep as is", "Move to silver") and not row["target"]])
print("target set where it must be blank:", [row["full_name"] for row in rows if row["my_call"] in ("Delete", "Retire after repointing", "Your decision") and row["target"]])
print("my_call:", Counter(row["my_call"] for row in rows))
print("vs_sachin:", Counter(row["vs_sachin"] for row in rows))
print("confidence:", Counter(row["confidence"] for row in rows))
for row in rows:
    if row["vs_sachin"] == "Disagree" or row["my_call"] == "Your decision":
        print(row["sheet_row"], row["full_name"].split(".")[-1], row["my_call"], row["vs_sachin"])
