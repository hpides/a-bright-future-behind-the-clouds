# Benchbase TPC-C on CedarDB and Postgres  

## Quick start - Run TPC-C CedarDB || Postgres on container start-up

This will:
1. Start CedarDB or Postgres, creating user
   `admin`, password `password`, database `benchbase`.
2. Wait for the DB to be healthy.
3. Build the Benchbase image and run TPC-C against it: create schema → load
   data → execute the workload.
4. Write results (latency/throughput CSVs, histograms) to `./results/DB_ENGINE`
   on your host.

Replace DB_ENGINE with cedardb or postgres
```bash
docker compose --env-file benchbase_config.env --profile DB_ENGINE up --build
```
## Stop containers and remove volumes with:

```bash
docker compose --env-file benchbase_config.env --profile DB_ENGINE down -v
```

## Build the DB container and run TPC-C independently

1. Start only the database (replace DB_ENGINE with cedardb or postgres)
```bash
   docker compose --env-file benchbase_config.env --profile DB_ENGINE up -d DB_ENGINE
```
2. Trigger the benchmark run
```bash
   docker compose --env-file benchbase_config.env --profile DB_ENGINE run --rm benchbase-DB_ENGINE
```

## Tuning the benchmark

The table below applies to `benchbase-cedardb`/`benchbase-postgres` (TPC-C
only. Defaults for these come from `benchbase_config.env`; use `docker run -e ...` /
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
