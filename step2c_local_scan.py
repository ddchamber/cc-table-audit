"""Step 2c: which local files mention each object (whole-word match on the bare table name).

Same intent as the skill's rg command; rg is not installed here. Word boundaries treat '_' as a word
character, so 'music_str_daily' does not match inside 'music_str_daily_nightly'.
"""
import csv
import json
import os
import re
from collections import defaultdict

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
SCAN_ROOTS: list[str] = [
    r"C:\Users\dan.chamberlin\TM\Music",
    r"C:\Users\dan.chamberlin\TM\VOC",
    r"C:\Users\dan.chamberlin\TM\voc-dashboard-v2",
    r"C:\Users\dan.chamberlin\TM\VOCtest",
    r"C:\Users\dan.chamberlin\Vault",
]
SCANNED_EXTENSIONS: set[str] = {".md", ".py", ".sql", ".yml", ".yaml", ".ipynb", ".json", ".txt", ".csv"}
SKIPPED_FOLDERS: set[str] = {".git", "node_modules", "venv", ".venv", "__pycache__", ".obsidian"}
MAX_FILE_BYTES: int = 3 * 1024 * 1024


def main() -> None:
    with open(os.path.join(AUDIT_FOLDER, "objects.csv"), encoding="utf-8") as objects_file:
        bare_names: set[str] = {row["full_name"].split(".")[-1] for row in csv.DictReader(objects_file)}
    name_pattern = re.compile(r"\b(" + "|".join(sorted(map(re.escape, bare_names), key=len, reverse=True)) + r")\b")

    files_by_name: dict[str, dict[str, int]] = defaultdict(dict)
    files_scanned: int = 0
    for scan_root in SCAN_ROOTS:
        for folder, subfolders, file_names in os.walk(scan_root):
            subfolders[:] = [s for s in subfolders if s not in SKIPPED_FOLDERS]
            for file_name in file_names:
                file_path = os.path.join(folder, file_name)
                if os.path.splitext(file_name)[1].lower() not in SCANNED_EXTENSIONS:
                    continue
                if os.path.getsize(file_path) > MAX_FILE_BYTES:
                    continue
                files_scanned += 1
                with open(file_path, encoding="utf-8", errors="ignore") as text_file:
                    for match in name_pattern.finditer(text_file.read()):
                        hits = files_by_name[match.group(1)]
                        hits[file_path] = hits.get(file_path, 0) + 1

    with open(os.path.join(AUDIT_FOLDER, "facts", "local_files.json"), "w", encoding="utf-8") as output_file:
        json.dump({"roots": SCAN_ROOTS, "files_scanned": files_scanned,
                   "by_object": {name: files_by_name.get(name, {}) for name in sorted(bare_names)}},
                  output_file, indent=2)
    unmentioned = sorted(name for name in bare_names if name not in files_by_name)
    print(f"scanned {files_scanned} files; {len(bare_names) - len(unmentioned)} of {len(bare_names)} names found")
    print("never mentioned locally:", unmentioned)


if __name__ == "__main__":
    main()
