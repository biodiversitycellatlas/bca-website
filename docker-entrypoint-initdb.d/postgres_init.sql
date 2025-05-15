/* PostgreSQL initialization script */

-- Activate trigram similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create databases if needed
CREATE DATABASE ghost;
