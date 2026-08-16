-- Warehouse bootstrap — runs once on first container start (empty data volume).
-- Creates the ELT layer schemas. The connecting user (POSTGRES_USER) owns them.
--
--   raw       -> landing zone for ingested source data, stored as-is
--   analytics -> cleaned / modelled data produced by dbt (staging, dims, facts, marts)

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;
