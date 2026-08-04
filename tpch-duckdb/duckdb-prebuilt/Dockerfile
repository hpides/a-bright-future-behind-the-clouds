# syntax=docker/dockerfile:1
#
# Uses DuckDB Labs' own pre-generated TPC-H databases
# (https://blobs.duckdb.org/data/tpch-sf<N>.db, documented at
# https://duckdb.org/docs/current/core_extensions/tpch) instead of
# generating data via dbgen on every run.
#
# The download itself happens OUTSIDE this build entirely — run
# ./download-data.sh [scale_factor] once first, which fetches the file
# into data/tpch-sf<N>.db (idempotent per scale factor: it skips the
# download if that file already exists). This Dockerfile just COPYs that
# already-local file into the image; the build itself never touches the
# network.

# This is a fast-path alternative to the duckdb-tpch profile (which uses
# dbgen and supports any scale factor via TPCH_SCALE_FACTOR at container
# runtime, no rebuild needed) — this one needs a rebuild any time you
# change TPCH_SF, since the data itself is baked into the
# image.
ARG TPCH_SF=1

FROM duckdb/duckdb:latest
ARG TPCH_SF
ENV TPCH_SF=${TPCH_SF}
#COPY data/tpch-sf${TPCH_SF}.db /data/tpch-sf${TPCH_SF}.db
COPY run_tpch_prebuilt.sql /scripts/run_tpch_prebuilt.sql
