SELECT table_catalog, table_schema, table_name, table_type, table_owner, created, last_altered, comment
FROM system.information_schema.tables
WHERE (table_catalog = 'nonprod_shared_gold' AND table_schema='central_analytics_crd' AND table_name LIKE 'voc%' AND table_owner <> 'dan.chamberlin@ticketmaster.com')
   OR table_name LIKE 'mv\_voc%'
   OR (table_schema = 'qualtrics_ca' AND table_name IN ('question','question_response','survey','survey_response'))
ORDER BY 1,2,3
