"""Step 8 (2026-11-23): live facts on the 24 nonprod VOC objects for Dan's keep-or-delete talk.

Per object: last write, who has written it in 365 days, other readers in 90 days, and whether the
prod twin exists and when the prod twin was last written. Read-only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dbx_api import run_sql

WAREHOUSE_ID: str = "dbb3244d6fa2f0fc"

query = """
WITH nonprod AS (
  SELECT table_name, table_type, created, last_altered FROM system.information_schema.tables
  WHERE table_catalog='nonprod_shared_gold' AND table_schema='central_analytics_crd'
    AND table_name LIKE 'voc%' AND table_owner LIKE 'dan.chamberlin%'),
prod AS (
  SELECT table_name, last_altered prod_last_altered FROM system.information_schema.tables
  WHERE table_catalog='prod_shared_gold' AND table_schema='central_analytics_crd' AND table_name LIKE 'voc%'),
writes AS (
  SELECT target_table_name t, max(event_date) last_write,
         concat_ws(', ', collect_set(split(created_by,'@')[0])) writers
  FROM system.access.table_lineage
  WHERE event_date >= current_date()-365 AND target_table_catalog='nonprod_shared_gold'
    AND target_table_schema='central_analytics_crd' AND target_table_name LIKE 'voc%'
  GROUP BY 1),
reads AS (
  SELECT source_table_name t, count(DISTINCT created_by) other_readers,
         concat_ws(', ', collect_set(split(created_by,'@')[0])) reader_names, max(event_date) last_read
  FROM system.access.table_lineage
  WHERE event_date >= current_date()-90 AND source_table_catalog='nonprod_shared_gold'
    AND source_table_schema='central_analytics_crd' AND source_table_name LIKE 'voc%'
    AND created_by NOT LIKE 'dan.chamberlin%' AND created_by NOT LIKE 'sachin.dewangan%'
  GROUP BY 1)
SELECT n.table_name, n.table_type, date(n.created) created, w.last_write, w.writers,
       coalesce(r.other_readers,0) other_readers, r.reader_names, r.last_read,
       CASE WHEN p.table_name IS NOT NULL THEN 'yes' ELSE 'no' END prod_twin, date(p.prod_last_altered) prod_last_altered
FROM nonprod n LEFT JOIN writes w ON w.t=n.table_name LEFT JOIN reads r ON r.t=n.table_name
LEFT JOIN prod p ON p.table_name=n.table_name
ORDER BY n.table_name
"""
column_names, rows = run_sql(WAREHOUSE_ID, query)
print(" | ".join(column_names))
for row in rows:
    print(" | ".join("" if value is None else str(value) for value in row))
print(len(rows), "rows")
