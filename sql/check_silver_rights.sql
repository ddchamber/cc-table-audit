SELECT 'schema' AS level, catalog_name, schema_name, grantee, privilege_type, inherited_from
FROM system.information_schema.schema_privileges
WHERE catalog_name IN ('prod_shared_silver', 'nonprod_shared_silver') AND schema_name = 'central_analytics_enr'
UNION ALL
SELECT 'catalog', catalog_name, NULL, grantee, privilege_type, inherited_from
FROM system.information_schema.catalog_privileges
WHERE catalog_name IN ('prod_shared_silver', 'nonprod_shared_silver')
ORDER BY 1, 2, 4, 5
