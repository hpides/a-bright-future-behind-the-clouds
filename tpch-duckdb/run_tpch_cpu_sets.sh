#!/bin/bash
set -euo pipefail

# Runs with multiple cpuset values against a pre-generated
# TPC-H database at a fixed scale factor (duckdb-tpch-prebuilt /
# "duckdb-prebuilt" profile), rather than duckdb-tpch's dbgen-based
# generation. This removes dbgen's own run-to-run generation time from
# each iteration.
#
# TPCH_SF selects which scale factor to sweep CPU_SET_DB at — it stays
# fixed across the whole sweep (only CPU_SET_DB varies between
# iterations); set it via the TPCH_SF environment variable, e.g.:
#   TPCH_SF=30 ./sweep_cpu_set_db.sh
# Must be one of the scale factors DuckDB Labs actually publishes a file
# for (see duckdb-prebuilt/download-data.sh's VALID_SCALE_FACTORS) —
# anything else fails fast there with a clear error, before any build is
# attempted.
#
# CPU_SET_DB values are Docker --cpuset-cpus syntax, e.g. "0", "0-1",
# "0-3", "0,2,4,6" — same format docker-compose.yml's `cpuset:` field
# expects.
#
# Note for the plotting scripts: point --glob at
# results/duckdb-prebuilt/cpuset_*/tpch_summary.json for results produced
# by this script, not results/duckdb/... (that's the separate, dbgen-based
# duckdb-tpch profile's result tree).
#
# Usage:
#   ./run_tpch_cpu_sets.sh                        # TPCH_SF=1 (default), uses the default sweep below
#   TPCH_SF=30 ./run_tpch_cpu_sets.sh              # sweep CPU sets at SF30
#   TPCH_SF=30 ./run_tpch_cpu_sets.sh "0" "0-3"    # or pass your own cpuset values too

cd "$(dirname "$0")"

ENV_FILE="tpch_config.env"
PROFILE="duckdb-prebuilt"
MOUNT_DIR="results/duckdb-prebuilt"
RESULTS_DIR="results/duckdb-prebuilt/sf${TPCH_SF}"
TPCH_SF="${TPCH_SF:-1}"

CPU_SETS=("$@")
if [ ${#CPU_SETS[@]} -eq 0 ]; then
    #CPU_SETS=("0" "0-1" "0-3")
    CPU_SETS=("0" "0-1" "0-3" "0-7" "0-15" "0-31" "0-63" "0-127" "0-191")
fi

shopt -s nullglob
mkdir -p "${MOUNT_DIR}"
mkdir -p "${RESULTS_DIR}"

# Sanitizes a cpuset value (e.g. "0-3" or "0,2,4,6") into something safe to
# use as a directory name — cpuset syntax is normally filesystem-safe as-is,
# but this guards against unexpected characters (spaces, slashes) anyway.
sanitize() {
    printf '%s' "$1" | tr -c 'A-Za-z0-9_,-' '_'
}

for cpu_set in "${CPU_SETS[@]}"; do
    echo "=================================================="
    echo "==> CPU_SET_DB=${cpu_set} (TPCH_SF=${TPCH_SF})"
    echo "=================================================="

    echo "==> Building and running (CPU_SET_DB=${cpu_set}, TPCH_SF=${TPCH_SF}) ..."
    CPU_SET_DB="${cpu_set}" TPCH_SF="${TPCH_SF}" docker compose --env-file "${ENV_FILE}" --profile "${PROFILE}" up --build

    echo "==> Tearing down container and volume ..."
    docker compose --env-file "${ENV_FILE}" --profile "${PROFILE}" down -v

    dest="${RESULTS_DIR}/cpuset_$(sanitize "${cpu_set}")"
    echo "==> Moving results into ${dest} ..."
    rm -rf "${dest}"
    mkdir -p "${dest}"

    found_any=false
    for f in "${MOUNT_DIR}"/*; do
        base="$(basename "$f")"
        case "$base" in
            sf*) continue ;;   # don't descend into our own organized subfolders
        esac
        if [ -f "$f" ]; then
            mv "$f" "${dest}/"
            found_any=true
        fi
    done
    if [ "${found_any}" = "false" ]; then
        echo "!! No result files found directly under ${MOUNT_DIR} to move for CPU_SET_DB=${cpu_set}" >&2
    fi

    echo "==> Done with CPU_SET_DB=${cpu_set}."
    echo
done

echo "All CPU sets complete (TPCH_SF=${TPCH_SF}). Results organized under ${RESULTS_DIR}/cpuset_<value>/"
