-- For a NEW, EMPTY database only. Existing tables cause an error; no resets.
-- psql -X --set ON_ERROR_STOP=1 -d infraassess_test -f database/install.sql
\set ON_ERROR_STOP on
\ir schema.sql
-- Seed the historical completed work order before installing completion triggers.
\ir seed.sql
\ir triggers.sql
\ir views.sql
\ir functions.sql
\ir procedures.sql
\ir demo_incidents.sql
