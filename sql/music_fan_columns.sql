SELECT table_name, column_name, data_type
FROM prod_shared_gold.information_schema.columns
WHERE table_schema = 'central_analytics_crd'
  AND table_name LIKE 'music%'
  AND (lower(column_name) RLIKE 'email|phone|first_name|last_name|full_name|guid|member_id|fan_id|customer|user_id|account|address|contact|name')
ORDER BY table_name, column_name
