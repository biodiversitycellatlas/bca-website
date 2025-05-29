/* PostgreSQL initialization script */

-- Increase max_wal_size to reduce how often checkpoints occur
ALTER SYSTEM SET max_wal_size = '2GB';
SELECT pg_reload_conf();

-- Activate trigram similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create databases if needed
CREATE DATABASE ghost;
