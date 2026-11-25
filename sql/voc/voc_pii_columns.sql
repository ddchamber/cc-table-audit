SELECT table_catalog, table_name, column_name, data_type
FROM system.information_schema.columns
WHERE table_schema = 'central_analytics_crd' AND table_catalog IN ('prod_shared_gold','nonprod_shared_gold')
  AND table_name LIKE 'voc%'
  AND lower(column_name) RLIKE 'email|phone|first_name|last_name|full_name|interviewee|interviewer|respondent|contact|address|recipient|participant|person|_name$|^name'
ORDER BY 1,2,3
