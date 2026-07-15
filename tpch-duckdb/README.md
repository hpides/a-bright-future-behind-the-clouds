# TPC-H on DuckDB

## Quick start — DuckDB (TPC-H)

```bash
docker compose --env-file tpch_config.env --profile duckdb up --build
```

This runs entirely in memory in a single one-shot container — no separate
database service, no volume, nothing to tear down. It:
1. Installs and loads DuckDB's `tpch` extension.
2. Generates a TPC-H dataset at scale factor `TPCH_SCALE_FACTOR` (default `1`;
   override via `docker compose --env-file benchbase_config.env --profile duckdb run -e TPCH_SCALE_FACTOR=5 duckdb-tpch`).
3. Runs all 22 TPC-H queries, printing each query and its runtime to the
   container's logs (`.echo on` / `.timer on`).


## Stop containers and remove volumes with:

```bash
docker compose --env-file tpch_config.env --profile duckdb down -v
```
