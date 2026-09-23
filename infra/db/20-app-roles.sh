#!/bin/sh
set -eu

# psql variables quote passwords as SQL literals, never concatenate them into SQL.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 \
  --set=migrator_password="$MIGRATOR_PASSWORD" --set=api_password="$API_DB_PASSWORD" \
  --set=app_database="$POSTGRES_DB" <<'SQL'
CREATE ROLE kdmp_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'migrator_password';
CREATE ROLE kdmp_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'api_password';
REVOKE ALL ON DATABASE :"app_database" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"app_database" TO kdmp_migrator, kdmp_api;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO kdmp_migrator;
GRANT USAGE ON SCHEMA public TO kdmp_api;
ALTER DEFAULT PRIVILEGES FOR ROLE kdmp_migrator IN SCHEMA public GRANT SELECT ON TABLES TO kdmp_api;
SQL
