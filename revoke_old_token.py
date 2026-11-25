"""Revoke the old SQL-only token ('dbx-cc', created 2026-09-08) and prove it no longer works."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import call_api
from list_tokens import old_token_still_works, read_old_token

OLD_TOKEN_ID: str = "184b98c7710b608f1ad80e33938e235a3b0c4f15f7b063471d9fafde9231314d"

old_token = read_old_token()
call_api("POST", "/api/2.0/token/delete", {"token_id": OLD_TOKEN_ID})
print("revoked dbx-cc;", old_token_still_works(old_token))
print("remaining:", [t["comment"] for t in call_api("GET", "/api/2.0/token/list").get("token_infos", [])])
print("new token still works:", call_api("GET", "/api/2.0/preview/scim/v2/Me").get("userName"))
