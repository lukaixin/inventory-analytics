# Backend instructions

## Stack

Python FastAPI + SQLAlchemy; persistence: DuckDB via duckdb-engine now; migration: Alembic with dialect adapter. PostgreSQL is a future target, not a currently verified runtime.

Keep transport handlers/controllers thin, business rules in services, and persistence in repositories/data access when those boundaries add clarity. Use typed request/response DTOs, boundary validation, centralized safe error handling, appropriate HTTP statuses, and maintained OpenAPI/Swagger. Keep health/readiness behavior and SQL/application logging useful without exposing secrets.

Schema changes require a tracked migration and safe seed-data handling. Focus tests on changed business behavior, validation, and data access. Run `python -m pytest` using isolated temporary DuckDB files. Never truncate development or unrelated databases. Run `python -m alembic upgrade head` and actual readiness checks; state unavailable dependencies or unrun checks.

Read root AGENTS and docs contracts. Money uses Decimal/Numeric and API decimal strings; legacy payload is immutable generic JSON with explicit schema_version. Unknown values remain null. Every data endpoint applies the shared server-side AccessPolicy. Preview writes only ImportBatch staging; commit is a single atomic/idempotent transaction. Isolate DB-specific connection, types and locking; DuckDB runs one backend writer process with application locking, not multiple uvicorn workers. Dev auth cannot be enabled in production. Local `.env` is at project root; API default port 8170. Expose frontend dist as optional static assets after API routes for simple single-origin runtime.
