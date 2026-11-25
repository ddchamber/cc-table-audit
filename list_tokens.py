"""List Dan's Databricks personal tokens (ids and metadata only; the API never returns token values).

Marks which one is the old SQL-only token by testing it: the old value from the backup file gets 403 on the
dashboards API, the new one does not. Read-only.
"""
import datetime
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import DATABRICKS_HOST, call_api

BACKUP_BASHRC: str = os.path.expanduser("~/.bashrc.bak-2026-11-18")


def read_old_token() -> str:
    with open(BACKUP_BASHRC, encoding="utf-8") as backup_file:
        return re.search(r'DATABRICKS_TOKEN="([^"]+)"', backup_file.read()).group(1)


def old_token_still_works(old_token: str) -> str:
    request = urllib.request.Request(f"{DATABRICKS_HOST}/api/2.0/preview/scim/v2/Me",
                                     headers={"Authorization": f"Bearer {old_token}"})
    try:
        with urllib.request.urlopen(request, timeout=60):
            return "old token still valid"
    except urllib.error.HTTPError as http_error:
        return f"old token returns HTTP {http_error.code}"


def main() -> None:
    old_token = read_old_token()
    print(old_token_still_works(old_token), "| old token ends ...", old_token[-4:])
    for token_info in call_api("GET", "/api/2.0/token/list").get("token_infos", []):
        created = datetime.datetime.fromtimestamp(token_info["creation_time"] / 1000, datetime.timezone.utc)
        expiry_ms = token_info.get("expiry_time", -1)
        expires = "never" if expiry_ms in (-1, 0) else datetime.datetime.fromtimestamp(
            expiry_ms / 1000, datetime.timezone.utc).date()
        print(token_info["token_id"], "| created", created.strftime("%Y-%m-%d %H:%M"), "| expires", expires,
              "| comment:", token_info.get("comment"), "| scopes:", token_info.get("scopes"))


if __name__ == "__main__":
    main()
