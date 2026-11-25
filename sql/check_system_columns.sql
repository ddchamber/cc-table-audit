SELECT table_schema, table_name, concat_ws(', ', collect_list(column_name)) AS column_list
FROM system.information_schema.columns
WHERE table_catalog = 'system'
  AND (table_schema, table_name) IN (
    ('access', 'table_lineage'), ('lakeflow', 'jobs'), ('lakeflow', 'job_run_timeline'),
    ('lakeflow', 'job_task_run_timeline'), ('access', 'audit'))
GROUP BY table_schema, table_name
