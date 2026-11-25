"""Resolve the prod silver schema owner (a service principal application id) to its display name."""
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import call_api

SILVER_OWNER_APPLICATION_ID: str = "29ac445e-6d1e-46f8-b386-903e044984c9"
search_filter = urllib.parse.quote(f'applicationId eq "{SILVER_OWNER_APPLICATION_ID}"')
found = call_api("GET", f"/api/2.0/preview/scim/v2/ServicePrincipals?filter={search_filter}")
for principal in found.get("Resources", []):
    print(principal.get("displayName"), principal.get("applicationId"), [g.get("display") for g in principal.get("groups", [])])
if not found.get("Resources"):
    print("not found in this workspace")
