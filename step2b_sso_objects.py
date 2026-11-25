"""Step 2b: dashboards, Genie spaces and job definitions through the SDK's SSO login.

The personal token is SQL-only (403 'missing scopes' on dashboards, genie, jobs, workspace), so these
reads use the cached external-browser OAuth login instead. Run with the databricks-mcp venv python.
"""
import csv
import json
import os

from databricks.sdk import WorkspaceClient

AUDIT_FOLDER: str = os.path.dirname(os.path.abspath(__file__))
FACTS_FOLDER: str = os.path.join(AUDIT_FOLDER, "facts")
WORKSPACE_HOST: str = "https://ticketmaster-cds-analytics.cloud.databricks.com"


def main() -> None:
    # Drop the SQL-only token from this process so the SDK uses the SSO login rather than the PAT.
    os.environ.pop("DATABRICKS_TOKEN", None)
    workspace = WorkspaceClient(host=WORKSPACE_HOST, auth_type="external-browser")
    print("signed in as", workspace.current_user.me().user_name)

    with open(os.path.join(AUDIT_FOLDER, "objects.csv"), encoding="utf-8") as objects_file:
        full_names: list[str] = [row["full_name"] for row in csv.DictReader(objects_file)]

    # Dashboards seen in lineage: name, path, and every dataset's SQL (for the breakage check).
    dashboard_ids: set[str] = set()
    with open(os.path.join(FACTS_FOLDER, "q2_readers_90d.csv"), encoding="utf-8") as readers_file:
        for row in csv.DictReader(readers_file):
            if row["read_via"].startswith("DASHBOARD"):
                dashboard_ids.update(i.strip() for i in row["entity_ids"].split(",") if i.strip())
    dashboards: list[dict] = []
    for dashboard_id in sorted(dashboard_ids):
        try:
            dashboard = workspace.lakeview.get(dashboard_id)
            serialized = json.loads(dashboard.serialized_dashboard or "{}")
            datasets = [{"name": d.get("displayName") or d.get("name"),
                         "sql": "".join(d.get("queryLines") or [d.get("query", "")])}
                        for d in serialized.get("datasets", [])]
            dashboards.append({"id": dashboard_id, "name": dashboard.display_name, "path": dashboard.path,
                               "state": str(dashboard.lifecycle_state), "warehouse_id": dashboard.warehouse_id,
                               "datasets": datasets})
        except Exception as error:  # keep going; record which dashboard could not be read and why
            dashboards.append({"id": dashboard_id, "error": f"{type(error).__name__}: {error}"[:300]})
    with open(os.path.join(FACTS_FOLDER, "q5_dashboards.json"), "w", encoding="utf-8") as output_file:
        json.dump(dashboards, output_file, indent=2)
    print(f"dashboards: {len(dashboards)} ({sum('error' in d for d in dashboards)} unreadable)")

    # Genie: an object is in a space only if its full name appears in the serialized definition.
    genie_matches: list[dict] = []
    genie_errors: list[str] = []
    spaces: list = []
    page_token = None
    while True:
        page = workspace.genie.list_spaces(page_token=page_token)
        spaces.extend(page.spaces or [])
        page_token = page.next_page_token
        if not page_token:
            break
    for space in spaces:
        try:
            detail = workspace.genie.get_space(space.space_id, include_serialized_space=True)
            serialized_text = (detail.serialized_space or "").lower()
        except Exception as error:
            genie_errors.append(f"{space.space_id} {space.title}: {type(error).__name__}")
            continue
        for full_name in full_names:
            if full_name.lower() in serialized_text:
                genie_matches.append({"full_name": full_name, "space_id": space.space_id, "space_title": space.title})
    with open(os.path.join(FACTS_FOLDER, "q5_genie.json"), "w", encoding="utf-8") as output_file:
        json.dump({"spaces_checked": len(spaces), "unreadable": genie_errors, "matches": genie_matches},
                  output_file, indent=2)
    print(f"genie: {len(spaces)} spaces, {len(genie_errors)} unreadable, {len(genie_matches)} matches")

    # Writer job definitions (task list and notebook paths) for the breakage check.
    job_definitions: list[dict] = []
    with open(os.path.join(FACTS_FOLDER, "q4_jobs.csv"), encoding="utf-8") as jobs_file:
        for row in csv.DictReader(jobs_file):
            try:
                job = workspace.jobs.get(int(row["job_id"]))
                job_definitions.append({"job_id": row["job_id"], "name": job.settings.name,
                                        "run_as": job.run_as_user_name, "settings": job.settings.as_dict()})
            except Exception as error:
                job_definitions.append({"job_id": row["job_id"], "error": f"{type(error).__name__}: {error}"[:300]})
    with open(os.path.join(FACTS_FOLDER, "q4_job_definitions.json"), "w", encoding="utf-8") as output_file:
        json.dump(job_definitions, output_file, indent=2)
    print(f"job definitions: {len(job_definitions)}")


if __name__ == "__main__":
    main()
