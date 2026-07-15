# TPC-H Extension on DuckDB

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
4. Writes two JSON files to `results/duckdb`, in JSON format:
   - `tpch_query_latency.json` — `[{"query_nr": ..., "latency_seconds": ...}, ...] for each of the 22 queries.
   - `tpch_summary.json` — a single-element array with `scale_factor`,
     `dbgen_seconds`, `total_query_seconds`, and a simplified
     `queries_per_second`/`queries_per_hour` throughput figure (query count
     ÷ wall-clock time to run all 22 sequentially — **not** the official
     TPC-H Composite Query-per-Hour metric, which uses a geometric mean
     across a power test and a multi-stream throughput test).


## Stop containers and remove volumes with:

```bash
docker compose --env-file tpch_config.env --profile duckdb down -v
```
