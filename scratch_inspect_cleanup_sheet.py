"""One-off: count Dan's objects by environment and suggested call in the schema-cleanup workbook."""
import sys
from collections import Counter
import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
workbook_path: str = r"C:\Users\dan.chamberlin\Downloads\Central Analytics schema cleanup review 2026-11-16.xlsx"
workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)

all_rows = list(workbook["All objects"].iter_rows(values_only=True))
header: list[str] = list(all_rows[0])
dan_rows = [dict(zip(header, row)) for row in all_rows[1:] if row and row[0] == "Dan Chamberlin"]
print("Dan objects in All objects:", len(dan_rows))
print("by env:", Counter(row["Environment"] for row in dan_rows))
print("by schema:", Counter(row["Current schema"] for row in dan_rows))
print("by call:", Counter((row["Environment"], row["Suggested call"]) for row in dan_rows))
print("by type:", Counter(row["Type"] for row in dan_rows))
prefixes = Counter(str(row["Table name"]).lstrip("↳ ").split("_")[0] for row in dan_rows)
print("by prefix:", prefixes)

# Section header rows on Dan's tab, plus whether columns R+ are already filled.
for row_index, row in enumerate(workbook["Dan Chamberlin"].iter_rows(values_only=True), start=1):
    first_cell = str(row[0] or "")
    if first_cell.startswith(("PROD", "PREPROD", "NONPROD")):
        print(row_index, first_cell)
    if len(row) > 17 and any(value is not None for value in row[17:]):
        print("columns R+ filled on row", row_index)
        break
