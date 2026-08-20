#!/bin/bash
# Cleanup legacy tables and indexes for Liara DB (run as postgres user)

set -e

DB_NAME="liara_db"


psql -d "$DB_NAME" <<EOF
# Drop dependent views first (CASCADE)
DROP VIEW IF EXISTS v_web_top_blocked CASCADE;
DROP VIEW IF EXISTS v_web_daily_stats CASCADE;
DROP VIEW IF EXISTS v_web_user_activity CASCADE;
DROP VIEW IF EXISTS v_recent_memory_context CASCADE;
DROP VIEW IF EXISTS v_active_sessions CASCADE;
EOF

psql -d "$DB_NAME" <<EOF
DROP INDEX IF EXISTS idx_web_logs_blocked;
DROP INDEX IF EXISTS idx_web_logs_created;
DROP INDEX IF EXISTS idx_web_logs_risk;
DROP INDEX IF EXISTS idx_web_logs_url;
DROP INDEX IF EXISTS idx_web_logs_user;
DROP TABLE IF EXISTS web_access_logs CASCADE;
DROP INDEX IF EXISTS idx_temporal_mood;
DROP INDEX IF EXISTS idx_temporal_sequence;
DROP INDEX IF EXISTS idx_temporal_session;
DROP INDEX IF EXISTS idx_temporal_user_timestamp;
DROP TABLE IF EXISTS temporal_index CASCADE;
DROP INDEX IF EXISTS idx_search_history_consent;
DROP INDEX IF EXISTS idx_search_history_user;
DROP TABLE IF EXISTS user_search_history;
DROP INDEX IF EXISTS idx_privacy_settings_user;
DROP TABLE IF EXISTS user_privacy_settings;
DROP INDEX IF EXISTS idx_user_location_consent;
DROP INDEX IF EXISTS idx_user_location_user;
DROP TABLE IF EXISTS user_location_preferences;
DROP INDEX IF EXISTS idx_blocked_keywords_category;
DROP INDEX IF EXISTS idx_blocked_keywords_keyword;
DROP INDEX IF EXISTS idx_blocked_keywords_log;
DROP TABLE IF EXISTS web_blocked_keywords;
DROP INDEX IF EXISTS idx_semantic_embedding_hnsw;
DROP INDEX IF EXISTS idx_semantic_importance;
DROP INDEX IF EXISTS idx_semantic_intent;
DROP INDEX IF EXISTS idx_semantic_type;
DROP INDEX IF EXISTS idx_semantic_user;
DROP TABLE IF EXISTS semantic_metadata CASCADE;
DROP INDEX IF EXISTS idx_relations_neo4j_sync;
DROP INDEX IF EXISTS idx_relations_source;
DROP INDEX IF EXISTS idx_relations_strength;
DROP INDEX IF EXISTS idx_relations_target;
DROP INDEX IF EXISTS idx_relations_type;
DROP TABLE IF EXISTS content_relations;
DROP INDEX IF EXISTS idx_rate_violations_ip;
DROP INDEX IF EXISTS idx_rate_violations_user;
DROP TABLE IF EXISTS web_rate_limit_violations;
DROP INDEX IF EXISTS idx_domain_rep_category;
DROP INDEX IF EXISTS idx_domain_rep_domain;
DROP INDEX IF EXISTS idx_domain_rep_score;
DROP TABLE IF EXISTS web_domain_reputation;
DROP INDEX IF EXISTS idx_session_active;
DROP INDEX IF EXISTS idx_session_redis;
DROP INDEX IF EXISTS idx_session_user;
DROP TABLE IF EXISTS session_memory CASCADE;
EOF

echo "✅ Legacy tables and indexes cleaned up. You can now rerun Alembic migrations."
