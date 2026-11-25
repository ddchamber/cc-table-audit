SELECT table_catalog, table_schema, table_name, table_type, table_owner, created
FROM system.information_schema.tables
WHERE table_name LIKE 'mv\_voc%' OR table_name LIKE 'mv\_music%'
ORDER BY 1, 2, 3
