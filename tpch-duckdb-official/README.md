# Benchbase TPC-C on CedarDB and Postgres, TPC-H on DuckDB

Runs the TPC-C benchmark from [CedarDB's Benchbase fork](https://github.com/cedardb/benchbase)
against either [CedarDB](https://cedardb.com/) or plain Postgres
(`postgres:18.4-trixie`) in Docker, so you can run the same workload against
either engine and compare — plus a DuckDB profile that runs TPC-H instead of
TPC-C, for reasons explained below.

This deliberately builds `cedardb/benchbase`, **not** upstream
`cmu-db/benchbase`. CedarDB speaks the Postgres wire protocol, so the JDBC
driver and connection URL are the same as for Postgres — but CedarDB's SQL
support has a few real differences from Postgres (e.g. it doesn't support
`CASCADE` on `DROP TABLE`, and a couple of TPC-C queries need slightly
different SQL). CedarDB's fork adds a dedicated `CEDARDB` database type with
its own `ddl-cedardb.sql` and `dialect-cedardb.xml` for TPC-C to handle this.
The same fork still ships the standard `POSTGRES` database type unmodified,
which is what the Postgres path uses. The Maven build always uses the
`postgres` profile — that profile only controls which JDBC driver gets
bundled, not the SQL dialect (which is picked at runtime by `<type>`).

There is deliberately **no default engine**, at either layer. The entrypoint
requires `DB_ENGINE` (`cedardb` or `postgres`) and refuses to start without
it; `docker-compose.yml` mirrors that — both engines sit behind their own
compose profile (`cedardb` / `postgres`), so `docker compose up` on its own
starts nothing until you pick one.

### Why DuckDB gets TPC-H instead of TPC-C

DuckDB doesn't fit the same mold as CedarDB/Postgres, for two reasons:

1. **Benchbase has no DuckDB support at all** — no `DatabaseType`, no
   `ddl-duckdb.sql`/dialect file, no JDBC driver dependency in any Maven
   profile. Neither the CedarDB fork nor upstream `cmu-db/benchbase` has ever
   had one.
2. **DuckDB is embedded/in-process, not client-server.** CedarDB and Postgres
   are databases a separate container listens on a port for; Benchbase (or
   anything else) connects over the network. DuckDB has no equivalent — it's
   a library a process opens a file with directly. (DuckDB shipped an actual
   client-server protocol called *Quack* in May 2026, but it's HTTP-based, in
   beta, not something a JDBC driver speaks, and — per DuckDB's own
   announcement — explicitly *not* aimed at "high-frequency OLTP with many
   small transactions," which is exactly what TPC-C is.)

TPC-C itself is also a poor fit even ignoring the tooling gap: it's a
heavy single-row OLTP write workload hitting shared hot rows (warehouse/
district counters) under many concurrent terminals. DuckDB uses optimistic
concurrency control, so that access pattern mostly produces transaction-
conflict aborts rather than a meaningful throughput number — it's not built
for this, by design.

So the `duckdb` profile runs DuckDB's own built-in `tpch` extension instead —
generates a TPC-H dataset and executes all 22 analytical queries, which is
exactly the workload DuckDB is built for. It doesn't go through Benchbase,
doesn't build anything, and uses the official `duckdb/duckdb` CLI image
directly, with `run_tpch.sql` bind-mounted in so you can edit it and just
re-run — no rebuild needed.

> **Before your first run:** make sure `duckdb/run_tpch.sql` already exists
> as a real file on your host. If it's missing when Compose first starts
> this service, Docker doesn't error — it silently bind-mounts an empty,
> root-owned *directory* into that path instead, and the container exits
> immediately with no output and no error, having run nothing. See the
> "Notes" section below for how to recover if this happens to you.

## What's in here

- `benchbase.env` — the single source of truth for credentials, host ports,
  and tuning values, substituted into `docker-compose.yml` via `${VAR}`
  references. **Not auto-loaded** — every `docker compose` command in this
  README passes `--env-file benchbase.env` explicitly (see "Configuring via
  `benchbase.env`" below for why). Same DB credentials are used for CedarDB
  and Postgres, and for the matching `benchbase-*` client — defined once
  here rather than hardcoded separately on each service.
- `Dockerfile` — multi-stage build: compiles Benchbase from source (postgres
  profile, requires JDK 23) in stage 1, then copies the runnable distribution
  into a slim JRE image.
- `config/tpcc_config.xml` — a single TPC-C config template shared by both
  engines. `DB_TYPE` and `DB_ISOLATION` (along with the connection details)
  are substituted at container start based on `DB_ENGINE`.
- `entrypoint.sh` — requires `DB_ENGINE` (`cedardb` or `postgres`, no
  default), derives `DB_TYPE`/`DB_ISOLATION` from it, waits for that database
  to accept connections, renders the config, then runs `benchbase.jar -b tpcc`.
- `docker-compose.yml` — defines `cedardb` + `benchbase-cedardb` (behind the
  `cedardb` compose profile), `postgres` + `benchbase-postgres` (behind the
  `postgres` compose profile), and `duckdb-tpch` (behind the `duckdb`
  compose profile). Nothing starts without picking a profile. Shared tuning
  env vars and the Postgres-wire-protocol healthcheck are factored out as
  YAML anchors (`x-tpcc-tuning`, `x-pg-healthcheck`) to avoid repeating them
  per service; the values inside those anchors come from `benchbase.env`.
- `duckdb/run_tpch.sql` — the script `duckdb-tpch` bind-mounts and runs:
  installs the `tpch` extension, generates a dataset at scale factor
  `TPCH_SCALE_FACTOR`, runs all 22 TPC-H queries (live progress visible via
  `.echo on` / `.timer on` in the container's logs), and writes exact
  per-query latency plus an aggregate throughput figure to
  `results/duckdb/tpch_query_latency.json` / `tpch_summary.json`. Must exist
  as a real file before the first run — see the warning under "Quick start
  — DuckDB" below.
- `tpch-official/Dockerfile` / `tpch-official/entrypoint.sh` —
  `duckdb-tpch-official` builds this image: compiles the real TPC-H
  `dbgen`/`qgen` toolkit from
  [duckdb/duckdb-tpch-power-test](https://github.com/duckdb/duckdb-tpch-power-test)
  (cloned at build time), then the entrypoint validates `TPCH_SCALE_FACTOR`,
  generates data (cached in a named volume), runs the official
  Power/Throughput/Composite benchmark, and writes a structured JSON
  summary plus the full run log to `results/duckdb-official`.
- `scripts/fix-permissions.sh` — pre-creates every `results/*` directory
  that gets bind-mounted at runtime, so Docker never has to auto-create any
  of them itself as root, then `chmod 777`s the whole project tree's
  directories. Run it once up front, or any time you hit a permission error
  caused by Docker having auto-created a root-owned path:
  ```bash
  ./scripts/fix-permissions.sh
  ```

## Configuring via `benchbase.env`

All the values that used to be hardcoded directly in `docker-compose.yml` —
DB credentials, host ports, TPC-C tuning, TPC-H scale factor — live in
`benchbase.env`, in the same directory as the compose file. To change
something, edit that file rather than editing the YAML:

```bash
# benchbase.env
DB_USER=admin
DB_PASSWORD=password
DB_NAME=benchbase
CEDARDB_HOST_PORT=5432
POSTGRES_HOST_PORT=5433
TPCC_WAREHOUSES=10
TPCC_TERMINALS=4
TPCC_DURATION_SEC=60
BENCHBASE_CREATE=true
BENCHBASE_LOAD=true
BENCHBASE_EXECUTE=true
TPCH_SCALE_FACTOR=1
```

**This file is not auto-loaded.** Docker Compose only auto-loads a file
literally named `.env`; any other name — including this one — requires
`--env-file benchbase.env` on every `docker compose` invocation, which is why
every command in this README includes it. If you drop the flag, Compose
does **not** error — it silently falls back to the inline defaults already
baked into `docker-compose.yml` (which happen to match `benchbase.env`'s
defaults, so a dropped flag can go unnoticed until you actually change a
value and wonder why it didn't take effect). If you'd rather have automatic
loading with no flag to remember, rename this file back to `.env`.

`DB_USER`/`DB_PASSWORD`/`DB_NAME` are shared between the database container
(`cedardb`'s `CEDAR_*` vars or `postgres`'s `POSTGRES_*` vars) and its
matching `benchbase-*` client's `DB_USER`/`DB_PASSWORD`/`DB_NAME` — so
changing a password only means changing it in one place, and the two sides
can never drift out of sync. You can also override any single value
one-off without touching the file at all — a shell-exported variable takes
precedence over `benchbase.env`:
```bash
TPCC_WAREHOUSES=50 docker compose --env-file benchbase.env --profile cedardb up --build
```

These are local dev/benchmark defaults, not real secrets, so `benchbase.env`
is safe to keep checked in as-is here — but it's a normal habit to
`.gitignore` it
once real credentials go in.

## Quick start — CedarDB

```bash
docker compose --env-file benchbase.env --profile cedardb up --build
```

This will:
1. Start CedarDB (Postgres-compatible, port 5432 on the host), creating user
   `admin`, password `password`, database `benchbase`.
2. Wait for CedarDB to be healthy.
3. Build the Benchbase image and run TPC-C against it: create schema → load
   data → execute the workload.
4. Write results (latency/throughput CSVs, histograms) to `./results/cedardb`
   on your host.

## Quick start — Postgres

The `postgres` service uses the official `postgres:18.4-trixie` image and is
entirely independent of CedarDB — its own container, port, and volume. It
only starts if you ask for the `postgres` profile:

```bash
docker compose --env-file benchbase.env --profile postgres up --build
```

This starts Postgres on host port **5433** (to avoid clashing with CedarDB on
5432), runs the same TPC-C workload against it, and writes results to
`./results/postgres`.

## Running both to compare

Combine profiles to bring up both stacks side by side:

```bash
docker compose --env-file benchbase.env --profile cedardb --profile postgres up --build
```

Tear everything down (and wipe both volumes) with:

```bash
docker compose --env-file benchbase.env --profile cedardb --profile postgres down -v
```

## Quick start — DuckDB (TPC-H, not TPC-C)

```bash
mkdir -p results/duckdb   # must exist before the first run — see Notes
docker compose --env-file benchbase.env --profile duckdb up --build
```

This runs the database itself entirely in memory in a single one-shot
container — no database volume, nothing to tear down — but does write two
result files to `results/duckdb`. It:
1. Installs and loads DuckDB's `tpch` extension.
2. Generates a TPC-H dataset at scale factor `TPCH_SCALE_FACTOR` (default `1`;
   override via `docker compose --env-file benchbase.env --profile duckdb run -e TPCH_SCALE_FACTOR=5 duckdb-tpch`).
3. Runs all 22 TPC-H queries, bracketing each with a real timestamp so
   latency is measured exactly (not parsed from `.timer` text) — query text
   and progress still print live to the container's logs via `.echo on` /
   `.timer on`.
4. Writes two JSON files to `results/duckdb`, each a proper JSON array of
   objects (via DuckDB's native `COPY ... TO ... (FORMAT JSON, ARRAY true)`,
   not the CLI's `.output`):
   - `tpch_query_latency.json` — `[{"query_nr": ..., "latency_seconds": ...}, ...]`
     for each of the 22 queries.
   - `tpch_summary.json` — a single-element array with `scale_factor`,
     `dbgen_seconds`, `total_query_seconds`, and a simplified
     `queries_per_second`/`queries_per_hour` throughput figure (query count
     ÷ wall-clock time to run all 22 sequentially — **not** the official
     TPC-H Composite Query-per-Hour metric, which uses a geometric mean
     across a power test and a multi-stream throughput test).

## Quick start — DuckDB official TPC-H metric (Power/Throughput/QphH)

For the real thing — not an approximation — `duckdb-tpch-official` wraps
[DuckDB Labs' own reference implementation](https://github.com/duckdb/duckdb-tpch-power-test),
which compiles the actual official TPC-H `dbgen`/`qgen` toolkit and
implements the genuine Power Test (with RF1/RF2 refresh functions), the
genuine Throughput Test (real concurrent query streams + a live background
refresh stream), and the Composite QphH@Size metric — exactly what
`duckdb-tpch` above cannot do, since DuckDB's `tpch` SQL extension has no
refresh-function or query-permutation support at all.

```bash
mkdir -p results/duckdb-official
docker compose --env-file benchbase.env --profile duckdb-official up --build
```

This is a genuinely heavier thing than every other profile in this repo:
- **Real compile step.** The build stage compiles `dbgen`/`qgen` from C
  source (`build-essential` + `git`), confirmed working during development.
- **Real compute time and disk usage**, scaling with `TPCH_SCALE_FACTOR`
  (default `1`) — minutes at SF=1, much longer at higher scale factors.
  Generated data persists in the `tpch-official-data` named volume across
  runs (set `FORCE_REGENERATE=true` to force regeneration).
- **`TPCH_SCALE_FACTOR` must be one of `1, 10, 20, 30, 100, 300, 1000, 3000,
  10000`** — these are the only scale factors the TPC-H spec (§5.3.4)
  defines a required stream count for, and the benchmark script looks that
  count up directly; anything else fails fast with a clear error before any
  work starts, rather than an obscure crash mid-run.
- **A completely separate compose profile** (`duckdb-official`, not
  `duckdb`) specifically so it's never accidentally triggered by
  `--profile duckdb`.

Results land in `results/duckdb-official`:
- `tpch_official_run.log` — full console output from the benchmark run.
- `tpch_official_summary.json` — `tpch_power_at_size`, `tpch_throughput_at_size`,
  `tpch_qphh_at_size` (the real Composite metric), plus load/timing detail.
- `log-sf<N>-<timestamp>.tsv` — CPU/memory/disk I/O sampled once per second
  throughout the run.

> **Licensing note:** the TPC-H reference toolkit is distributed under the
> [TPC EULA](https://github.com/duckdb/duckdb-tpch-power-test/blob/main/tpch_tools_3.0.1/EULA.txt),
> which restricts publicly disclosing performance results produced with it —
> permitted only as an official, audited TPC Benchmark Result; as part of
> academic/research work; or otherwise clearly labeled as **not comparable**
> to an official TPC Benchmark Result. This setup is not an audited
> submission. `tpch_official_summary.json` carries that disclaimer in its
> own `note` field — keep it attached to anything you share.

## Tuning the benchmark

The table below applies to `benchbase-cedardb`/`benchbase-postgres` (TPC-C
only — `duckdb-tpch` just takes `TPCH_SCALE_FACTOR`, see above). Defaults for
these come from `benchbase.env`; use `docker run -e ...` /
`docker compose run -e ...` for one-off overrides without touching
`benchbase.env` (or the compose file) at all:

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
docker compose --env-file benchbase.env --profile cedardb run -e BENCHBASE_CREATE=false -e BENCHBASE_LOAD=false \
  -e BENCHBASE_EXECUTE=true benchbase-cedardb
# or: --profile postgres run ... benchbase-postgres
```

For a real benchmark run (not just a smoke test), scale warehouses and
terminals up substantially (e.g. 100+ warehouses, terminals ≈ warehouses × 1–2)
and increase `TPCC_DURATION_SEC` to several minutes, with a warmup period —
edit `config/tpcc_config.xml` to add a `<warmup>` element inside `<work>` if
you want a separate warmup phase excluded from the results.

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

Omitting `-e DB_ENGINE=...` fails immediately with:
```
DB_ENGINE must be set to 'cedardb' or 'postgres' — no default is provided
```

## Notes

- The build stage clones `main` of `cedardb/benchbase` (not `cmu-db/benchbase`)
  at build time — pin `BENCHBASE_REF` (a tag/commit) via `--build-arg` if you
  need a reproducible build.
- Benchbase currently requires JDK 23 to compile; the Dockerfile uses
  `eclipse-temurin:23-jdk-jammy` / `23-jre-jammy` accordingly.
- CedarDB's docker image never overwrites an existing database directory —
  if you restart with the same volume, it reconnects to what's already there
  and ignores `CEDAR_USER`/`CEDAR_PASSWORD` (the existing credentials apply).
- Postgres 18 changed its default data directory: the image now expects the
  volume mounted at `/var/lib/postgresql` (versioned subdirectory inside),
  not the older `/var/lib/postgresql/data` — already set correctly in
  `docker-compose.yml`.
- Use `docker compose --env-file benchbase.env --profile cedardb --profile postgres down -v` for a
  clean slate on both databases (drop the profile flags you didn't use).
- The container starts as root, but only to fix permissions on the bind-mounted
  `results` directory (Docker creates that mount as `root:root` if it doesn't
  already exist on the host, and only root can `chmod` it). The entrypoint
  adds write permission for all users, then drops privileges to an
  unprivileged `benchbase` user before actually running Benchbase.
- `duckdb/run_tpch.sql` reads `TPCH_SCALE_FACTOR` via DuckDB's `getenv()`
  function, which only exists in the DuckDB CLI (not other DuckDB clients) —
  fine here since `duckdb-tpch` only ever runs through the official CLI image.
- `duckdb-tpch` bind-mounts `duckdb/run_tpch.sql` instead of baking it into a
  custom image, so you can edit the script and just re-run — no rebuild
  needed. The tradeoff: **the file must exist on the host before the first
  run.** If it doesn't, Docker bind-mounts an empty, root-owned *directory*
  into that path instead of erroring — you'll see the container exit
  immediately with code 0 and no output. If that happens:
  ```bash
  sudo rmdir duckdb/run_tpch.sql   # remove the directory Docker created
  # then create duckdb/run_tpch.sql as a real file
  ```
  `scripts/fix-permissions.sh` doesn't cover this specific case (it's a
  missing-file problem, not a permissions problem) — this is the one thing
  in the repo you need to double-check exists before first bringing up the
  `duckdb` profile.
- **"cannot open '/results/...'" from `duckdb-tpch`:** DuckDB's official
  image confirmedly runs as root (its upstream `Dockerfile` has no `USER`
  directive), so this generally isn't a Unix-permission-bits problem —
  `chmod` can't be the fix. The most likely cause on Linux is SELinux
  (Fedora/RHEL/CentOS) blocking the container from writing to a bind-mounted
  host path regardless of Unix permissions; every bind mount in
  `docker-compose.yml` includes the `:z` option to relabel for this. If it
  still happens after pulling the latest `docker-compose.yml`:
  1. Confirm `results/duckdb` exists on the host and the mount actually
     attached: `docker compose --env-file benchbase.env --profile duckdb run --rm --entrypoint duckdb duckdb-tpch -c "SELECT * FROM glob('/results/*');"`
  2. Check for SELinux denials: `sudo ausearch -m avc -ts recent` (if
     `ausearch` isn't installed, `sudo dmesg | grep -i denied` often shows
     the same thing).
  3. As a last resort, `chcon -Rt svirt_sandbox_file_t results/duckdb`
     manually relabels the directory the same way `:z` does.
- **`duckdb-tpch-official` build time.** Compiling `dbgen`/`qgen` itself is
  fast (a few seconds); what actually takes time is `generate.sh` (runs the
  real data generator) and `benchmark.py` (runs the real Power + Throughput
  tests) inside the *entrypoint*, not the image build. `docker compose ...
  up --build` finishing quickly only means the image built — the container
  run afterward is the slow part, and scales with `TPCH_SCALE_FACTOR`.
- **`duckdb-tpch-official` and disk space.** Generated flat files, the
  DuckDB database file, and cached template all live in the
  `tpch-official-data` named volume. At higher scale factors (300+) this
  can reach tens of GB. `docker volume rm <project>_tpch-official-data`
  (after `docker compose --profile duckdb-official down`) reclaims it.
- **KeyError deep in `benchmark.py`** means `TPCH_SCALE_FACTOR` bypassed the
  entrypoint's validation somehow (e.g. set directly via `docker run -e`
  against the built image rather than through compose) — it must be exactly
  one of `1, 10, 20, 30, 100, 300, 1000, 3000, 10000`.
