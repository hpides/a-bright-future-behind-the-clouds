# Benchbase TPC-C on CedarDB and Postgres, TPC-H on DuckDB

## Quick start

This will:
1. Start CedarDB or Postgres, creating user
   `admin`, password `password`, database `benchbase`.
2. Wait for the DB to be healthy.
3. Build the Benchbase image and run TPC-C against it: create schema → load
   data → execute the workload.
4. Write results (latency/throughput CSVs, histograms) to `./results/DB_ENGINE`
   on your host.

## Run TPC-C CedarDB || Postgres on Start-up

```bash
# Replace DB_ENGINE with cedardb or postgres
docker compose --env-file benchbase_config.env --profile DB_ENGINE up --build
```
## Stop containers and remove volumes with:

```bash
docker compose --env-file benchbase_config.env --profile DB_ENGINE down -v
```

## Build the DB container and run TPC-C

```bash
   # Replace DB_ENGINE with cedardb or postgres
   # 1. Start only the database
   docker compose --env-file benchbase.env --profile DB_ENGINE up -d DB_ENGINE

   # 2. Whenever you want — trigger the benchmark run
   docker compose --env-file benchbase.env --profile DB_ENGINE run --rm benchbase-DB_ENGINE
```

## Running against an existing database instance

If you already have CedarDB or Postgres running elsewhere, skip
`docker-compose` and just run the Benchbase image directly, pointing it at
your host. `DB_ENGINE` is still required:

```bash
docker build -t benchbase-tpcc .

# CedarDB
docker run --rm \
  -e DB_ENGINE=cedardb \
  -e DB_HOST=my-cedardb-host -e DB_PORT=5432 \
  -e DB_NAME=benchbase -e DB_USER=admin -e DB_PASSWORD=password \
  -v "$(pwd)/results:/benchbase/results" \
  benchbase-tpcc

# Postgres
docker run --rm \
  -e DB_ENGINE=postgres \
  -e DB_HOST=my-postgres-host -e DB_PORT=5432 \
  -e DB_NAME=benchbase -e DB_USER=admin -e DB_PASSWORD=password \
  -v "$(pwd)/results:/benchbase/results" \
  benchbase-tpcc
```

## Quick start — DuckDB (TPC-H)

```bash
docker compose --env-file benchbase_config.env --profile duckdb up --build
```

This runs entirely in memory in a single one-shot container — no separate
database service, no volume, nothing to tear down. It:
1. Installs and loads DuckDB's `tpch` extension.
2. Generates a TPC-H dataset at scale factor `TPCH_SCALE_FACTOR` (default `1`;
   override via `docker compose --env-file benchbase_config.env --profile duckdb run -e TPCH_SCALE_FACTOR=5 duckdb-tpch`).
3. Runs all 22 TPC-H queries, printing each query and its runtime to the
   container's logs (`.echo on` / `.timer on`).

To save the output, create the folder and redirect into it:
`mkdir -p results/duckdb && docker compose --env-file benchbase_config.env --profile duckdb up --build > results/duckdb/tpch-run.log 2>&1`.

## Tuning the benchmark

The table below applies to `benchbase-cedardb`/`benchbase-postgres` (TPC-C
only — `duckdb-tpch` just takes `TPCH_SCALE_FACTOR`, see above). Defaults for
these come from `benchbase_config.env`; use `docker run -e ...` /
`docker compose run -e ...` for one-off overrides without touching
`benchbase_config.env` (or the compose file) at all:

| Variable             | Default    | Meaning                                    |
|----------------------|------------|---------------------------------------------|
| `DB_ENGINE`          | **none — mandatory** | `cedardb` or `postgres`; container exits with an error if unset |
| `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` | service-dependent | Must match the target database's own env |
| `TPCC_WAREHOUSES`    | `10`       | Scale factor — number of TPC-C warehouses  |
| `TPCC_TERMINALS`     | `4`        | Concurrent simulated terminals             |
| `TPCC_DURATION_SEC`  | `60`       | Length of the measured run, in seconds     |
| `BENCHBASE_CREATE`   | `true`     | Create the schema                          |
| `BENCHBASE_LOAD`     | `true`     | Load the initial data                      |
| `BENCHBASE_EXECUTE`  | `true`     | Run the actual workload                    |

A common pattern: load once, then re-run execute-only against the same data:

```bash
docker compose --env-file benchbase_config.env --profile cedardb run -e BENCHBASE_CREATE=false -e BENCHBASE_LOAD=false \
  -e BENCHBASE_EXECUTE=true benchbase-cedardb
# or: --profile postgres run ... benchbase-postgres
```
