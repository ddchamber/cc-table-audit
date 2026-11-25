"""Test a new Databricks PAT on every scope the audit needs, then (with --apply) swap it into
~/.claude/settings.json and ~/.bashrc in place of the current DATABRICKS_TOKEN. Never prints the token.

Usage: python swap_token.py <new_token> [--apply]
"""
import json
import os
import sys
import urllib.error
import urllib.request

HOST: str = os.environ["DATABRICKS_HOST"].rstrip("/")
FILES_TO_UPDATE: list[str] = [os.path.expanduser("~/.claude/settings.json"), os.path.expanduser("~/.bashrc")]
SCOPE_PROBES: dict[str, str] = {
    "identity": "/api/2.0/preview/scim/v2/Me",
    "sql": "/api/2.0/sql/warehouses",
    "dashboards": "/api/2.0/lakeview/dashboards?page_size=1",
    "genie": "/api/2.0/genie/spaces?page_size=1",
    "jobs": "/api/2.1/jobs/get?job_id=489488962317323",
    "workspace": "/api/2.0/workspace/list?path=/Users/dan.chamberlin@ticketmaster.com",
    "unity_catalog": "/api/2.1/unity-catalog/catalogs?max_results=1",
}


def probe(token: str) -> dict[str, str]:
    results: dict[str, str] = {}
    for scope_name, path in SCOPE_PROBES.items():
        request = urllib.request.Request(f"{HOST}{path}", headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read() or b"{}")
                results[scope_name] = "OK" + (f" ({body.get('userName')})" if scope_name == "identity" else "")
        except urllib.error.HTTPError as http_error:
            results[scope_name] = f"HTTP {http_error.code}"
    return results


def main() -> None:
    new_token: str = sys.argv[1].strip()
    old_token: str = os.environ["DATABRICKS_TOKEN"]
    results = probe(new_token)
    for scope_name, outcome in results.items():
        print(f"{scope_name:14} {outcome}")
    if "--apply" not in sys.argv:
        return
    if any(not outcome.startswith("OK") for outcome in results.values()):
        sys.exit("not applied: at least one scope failed")
    for file_path in FILES_TO_UPDATE:
        with open(file_path, encoding="utf-8") as input_file:
            text = input_file.read()
        replacements = text.count(old_token)
        with open(file_path, "w", encoding="utf-8", newline="") as output_file:
            output_file.write(text.replace(old_token, new_token))
        print(f"{file_path}: replaced {replacements}")
    # Confirm settings.json still parses after the edit.
    with open(FILES_TO_UPDATE[0], encoding="utf-8") as settings_file:
        json.load(settings_file)
    print("settings.json parses OK")


if __name__ == "__main__":
    main()
