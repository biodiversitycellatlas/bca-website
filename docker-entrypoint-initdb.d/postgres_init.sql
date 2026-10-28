/* PostgreSQL initialization script */

-- Increase max_wal_size to reduce how often checkpoints occur
ALTER SYSTEM SET max_wal_size = '2GB'; -- noqa
SELECT pg_reload_conf();

-- Create databases if needed
CREATE DATABASE ghost;
