# syntax=docker/dockerfile:1
#
# Wraps DuckDB Labs' own reference implementation of the TPC-H benchmark
# (github.com/duckdb/duckdb-tpch-power-test), which vendors the *actual*
# official TPC-H reference toolkit (tpch_tools_3.0.1 — real dbgen/qgen C
# source) rather than DuckDB's convenience `tpch` SQL extension. This is
# what makes the real Power Test (with RF1/RF2 refresh functions), the real
# Throughput Test (concurrent streams + a live background refresh stream),
# and the Composite QphH@Size metric possible — none of which the `tpch`
# extension supports (its own docs: "It is not possible to change the query
# parameters using the tpch extension").
#
# NOTE ON LICENSING: the TPC-H reference toolkit is distributed under the
# TPC EULA (tpch_tools_3.0.1/EULA.txt in the cloned repo), which restricts
# publicly disclosing performance results produced with it — permitted only
# as an official audited TPC submission, as part of academic/research work,
# or otherwise clearly labeled as NOT comparable to an official TPC
# Benchmark Result. This wrapper is not an audited submission.
FROM python:3.12-slim

ARG TPCH_POWER_TEST_REPO=https://github.com/duckdb/duckdb-tpch-power-test.git
ARG TPCH_POWER_TEST_REF=main

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /bench

RUN git clone --depth 1 --branch "${TPCH_POWER_TEST_REF}" "${TPCH_POWER_TEST_REPO}" .

# requirements.txt pins duckdb==1.5.1 — matches upstream exactly, for
# reproducibility with what this harness was actually built/tested against.
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Builds dbgen + qgen. The repo's Makefile already has MACHINE=LINUX,
# DATABASE=VECTORWISE, WORKLOAD=TPCH, CC=gcc pre-configured — this is a
# straight `make`, no makefile.suite copying/editing needed.
RUN cd tpch_tools_3.0.1/dbgen && make

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 777 /usr/local/bin/entrypoint.sh

# TPCH_SCALE_FACTOR must be one of the values the TPC-H spec's §5.3.4
# scale-factor→stream-count table defines (1, 10, 20, 30, 100, 300, 1000,
# 3000, 10000) — benchmark.py looks the stream count up directly from that
# table and KeyErrors on anything else. The entrypoint validates this with
# a clear error message before running anything.
ENV TPCH_SCALE_FACTOR=1

ENTRYPOINT ["/bin/bash", "/usr/local/bin/entrypoint.sh"]
