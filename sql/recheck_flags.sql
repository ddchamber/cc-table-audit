-- Every write and every non-owner read of the flagged objects since 11-01, with how it happened.
SELECT 'write' AS kind, target_table_name AS object_name, created_by, entity_type, entity_id, event_date,
       count(*) AS events
FROM system.access.table_lineage
WHERE target_table_catalog = 'prod_shared_gold' AND target_table_schema = 'central_analytics_crd'
  AND target_table_name IN ('music_benchmark_events_b4b5', 'music_benchmark_events_ctrl',
                            'music_benchmark_stats_b4b5', 'music_benchmark_stats_ctrl',
                            'music_event_phase_summary_step22')
  AND event_date >= '2026-11-01'
GROUP BY 1, 2, 3, 4, 5, 6
UNION ALL
SELECT 'read', source_table_name, created_by, entity_type, entity_id, event_date, count(*)
FROM system.access.table_lineage
WHERE source_table_catalog = 'prod_shared_gold' AND source_table_schema = 'central_analytics_crd'
  AND source_table_name IN ('music_benchmark_events_b4b5', 'music_benchmark_events_ctrl',
                            'music_benchmark_stats_b4b5', 'music_benchmark_stats_ctrl',
                            'music_event_phase_summary_step22')
  AND event_date >= '2026-11-01' AND created_by <> 'dan.chamberlin@ticketmaster.com'
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY 2, 1, 6
