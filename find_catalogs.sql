SELECT table_catalog, table_schema, count(*) AS object_count
FROM system.information_schema.tables
WHERE table_schema = 'central_analytics_crd'
  AND (table_name LIKE 'music\_%' OR table_name LIKE 'voc\_%')
GROUP BY table_catalog, table_schema
ORDER BY table_catalog
