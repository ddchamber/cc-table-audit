-- Who can create or modify tables in the gold schema Dan writes today, and in the silver target.
SELECT 'schema' AS level, catalog_name, schema_name, grantee, concat_ws(', ', collect_set(privilege_type)) AS rights,
       is_account_group_member(grantee) OR grantee = current_user() AS dan_has_it
FROM system.information_schema.schema_privileges
WHERE ((catalog_name = 'prod_shared_gold' AND schema_name = 'central_analytics_crd')
    OR (catalog_name = 'prod_shared_silver' AND schema_name = 'central_analytics_enr'))
  AND privilege_type IN ('CREATE_TABLE', 'MODIFY', 'ALL_PRIVILEGES', 'MANAGE')
GROUP BY 1, 2, 3, 4
UNION ALL
SELECT 'catalog', catalog_name, NULL, grantee, concat_ws(', ', collect_set(privilege_type)),
       is_account_group_member(grantee) OR grantee = current_user()
FROM system.information_schema.catalog_privileges
WHERE catalog_name IN ('prod_shared_gold', 'prod_shared_silver')
  AND privilege_type IN ('CREATE_TABLE', 'MODIFY', 'ALL_PRIVILEGES', 'MANAGE', 'CREATE_SCHEMA')
GROUP BY 1, 2, 3, 4
ORDER BY 2, 1, 4
