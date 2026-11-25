"""Small Databricks REST helper for the table audit (read-only use).

Uses DATABRICKS_HOST and DATABRICKS_TOKEN from the environment, because the
databricks-sso MCP server hangs waiting on a browser sign-in.

Usage:
    python dbx_api.py whoami
    python dbx_api.py warehouses
    python dbx_api.py sql <warehouse_id> <path_to_sql_file> [output_csv]
"""
import csv
import json
import os
import sys
import time
import urllib.request

DATABRICKS_HOST: str = os.environ["DATABRICKS_HOST"].rstrip("/")
DATABRICKS_TOKEN: str = os.environ["DATABRICKS_TOKEN"]


def call_api(method: str, path: str, body: dict | None = None) -> dict:
    request_data: bytes | None = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{DATABRICKS_HOST}{path}",
        data=request_data,
        method=method,
        headers={"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read() or b"{}")


def run_sql(warehouse_id: str, sql_text: str) -> tuple[list[str], list[list]]:
    statement = call_api("POST", "/api/2.0/sql/statements", {
        "warehouse_id": warehouse_id,
        "statement": sql_text,
        "wait_timeout": "50s",
        "on_wait_timeout": "CONTINUE",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
    })
    statement_id: str = statement["statement_id"]
    # Poll because big lineage queries can outlast the 50 s synchronous wait.
    while statement["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        statement = call_api("GET", f"/api/2.0/sql/statements/{statement_id}")
    if statement["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(json.dumps(statement["status"], indent=2))
    column_names: list[str] = [column["name"] for column in statement["manifest"]["schema"]["columns"]]
    all_rows: list[list] = list(statement.get("result", {}).get("data_array", []) or [])
    next_chunk_link: str | None = statement.get("result", {}).get("next_chunk_internal_link")
    # Large results come back in chunks; follow every link so no rows are dropped.
    while next_chunk_link:
        chunk = call_api("GET", next_chunk_link)
        all_rows.extend(chunk.get("data_array", []) or [])
        next_chunk_link = chunk.get("next_chunk_internal_link")
    return column_names, all_rows


def main() -> None:
    command: str = sys.argv[1]
    if command == "whoami":
        user = call_api("GET", "/api/2.0/preview/scim/v2/Me")
        print(user.get("userName"))
    elif command == "warehouses":
        for warehouse in call_api("GET", "/api/2.0/sql/warehouses").get("warehouses", []):
            print(warehouse["id"], warehouse["state"], warehouse.get("cluster_size"), warehouse["name"])
    elif command == "sql":
        warehouse_id, sql_path = sys.argv[2], sys.argv[3]
        with open(sql_path, encoding="utf-8") as sql_file:
            column_names, all_rows = run_sql(warehouse_id, sql_file.read())
        if len(sys.argv) > 4:
            with open(sys.argv[4], "w", newline="", encoding="utf-8") as output_file:
                writer = csv.writer(output_file)
                writer.writerow(column_names)
                writer.writerows(all_rows)
            print(f"{len(all_rows)} rows -> {sys.argv[4]}")
        else:
            print("\t".join(column_names))
            for row in all_rows[:50]:
                print("\t".join("" if value is None else str(value) for value in row))
            print(f"({len(all_rows)} rows)")


if __name__ == "__main__":
    main()
