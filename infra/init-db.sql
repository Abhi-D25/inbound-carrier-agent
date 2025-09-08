-- Initialize the carrier database with proper settings

-- Create database if it doesn't exist (this runs in postgres default db)
-- The database is already created by docker-compose environment variables

-- Connect to the carrier_db and set up extensions
\c carrier_db;

-- Create extensions for better performance and functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better query performance
-- These will be created by SQLAlchemy, but we can add extra ones here

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON DATABASE carrier_db TO carrier_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO carrier_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO carrier_user;

-- Set default permissions for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO carrier_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO carrier_user;