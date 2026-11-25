"""Revoke the old SQL-only token ('dbx-cc', created 2026-09-08) by its id, then prove the new token still works.

Rewritten 2026-11-23 because the .bak-2026-11-18 backups (which held the old value) are already gone; revoking
by id does not need the value.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import call_api

OLD_TOKEN_ID: str = "184b98c7710b608f1ad80e33938e235a3b0c4f15f7b063471d9fafde9231314d"


def token_ids_and_comments() -> list[tuple[str, str]]:
    return [(t["token_id"], t.get("comment") or "") for t in call_api("GET", "/api/2.0/token/list").get("token_infos", [])]


before = token_ids_and_comments()
print("before:", [comment for _, comment in before])
if any(token_id == OLD_TOKEN_ID for token_id, _ in before):
    call_api("POST", "/api/2.0/token/delete", {"token_id": OLD_TOKEN_ID})
    print("revoked old token dbx-cc")
else:
    print("old token dbx-cc was already gone")
after = token_ids_and_comments()
assert all(token_id != OLD_TOKEN_ID for token_id, _ in after), "old token still listed"
print("after:", [comment for _, comment in after])
print("new token still works:", call_api("GET", "/api/2.0/preview/scim/v2/Me").get("userName"))
