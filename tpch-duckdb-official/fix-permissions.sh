#!/bin/bash
set -euo pipefail

# Pre-creates results/cedardb, results/postgres, results/duckdb, and
# results/duckdb-official — the directories Docker bind-mounts at runtime
# (Benchbase output for the first two, tpch_query_latency.json/
# tpch_summary.json for duckdb, tpch_official_summary.json + run log for
# duckdb-official) — so it never has to auto-create any of them itself as
# root on first run. (duckdb/ and config/ are build-context/COPY sources
# only, never bind-mounted at runtime, so they were never actually at risk
# of this.) Then chmods every directory in the project tree to 777.
#
# Run this once after cloning, or any time you hit a "Permission denied" /
# "not a directory" error caused by Docker having auto-created a root-owned
# path. Safe to re-run any time.
#
# Needs sudo because directories Docker already auto-created as root can't
# be chmod'd by a regular user — only root or the owner can do that.

cd "$(dirname "$0")/.."

mkdir -p results/cedardb results/postgres results/duckdb results/duckdb-official

sudo find . -type d -exec chmod 777 {} \;

echo "Done — every directory under $(pwd) is now 777."
