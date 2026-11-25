"""Probe which REST endpoints this token can read, to tell a scope limit from a sharing limit."""
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import call_api

PROBE_PATHS: list[str] = [
    "/api/2.0/lakeview/dashboards?page_size=5",
    "/api/2.0/lakeview/dashboards/01f1759764ba1ae3a9518d5311d3df25",
    "/api/2.0/genie/spaces?page_size=5",
    "/api/2.1/jobs/get?job_id=489488962317323",
    "/api/2.0/workspace/list?path=/Users/dan.chamberlin@ticketmaster.com",
]
for probe_path in PROBE_PATHS:
    try:
        response = call_api("GET", probe_path)
        print("OK ", probe_path, str(response)[:200])
    except urllib.error.HTTPError as http_error:
        print(http_error.code, probe_path, http_error.read()[:300])
