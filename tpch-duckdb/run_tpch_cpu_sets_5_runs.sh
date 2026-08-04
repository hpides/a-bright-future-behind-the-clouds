#!/bin/bash
set -euo pipefail

# Sweeps CPU_SET_DB across multiple cpuset values against a pre-generated
# TPC-H database at a fixed scale factor (duckdb-tpch-prebuilt /
# "duckdb-prebuilt" profile), rather than duckdb-tpch's dbgen-based
# generation. This removes dbgen's own run-to-run generation time from
# each iteration, so what's actually being measured is CPU_SET_DB's
# effect in isolation, not that effect on top of dbgen's variance.
#
# Each cpuset value is run REPS times (default 5, override via the REPS
# env var), not once — a single run is noisy (scheduling jitter, cache
# state, etc.), so this reports the average queries_per_second across
# REPS repetitions instead of trusting any single run.
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
# For each cpuset value, for each of REPS repetitions: ensures that scale
# factor's pre-generated data is downloaded first (idempotent — safe even
# if it already is; only actually needed once, but cheap to re-check),
# builds + runs (docker compose up --build, overriding CPU_SET_DB and
# TPCH_SF via shell-exported variables, which take precedence over
# tpch_config.env for that one run only — both stay the same value every
# repetition, so after the first build Docker's own cache means later
# repetitions' builds are near-instant no-ops), tears the container down
# (down -v), then moves that repetition's result files into
# cpuset_<value>/rep_<N>/ before the next repetition overwrites
# results/duckdb-prebuilt/tpch_summary.json / tpch_query_latency.json.
#
# After all REPS repetitions for a cpuset value are done, computes the
# arithmetic mean of queries_per_second (and queries_per_hour) across
# them, and writes it to cpuset_<value>/tpch_summary.json — same schema
# tpch_summary.json normally has, so the plotting scripts need no changes
# at all; they just see one (now-averaged) summary per cpuset folder,
# same as before. The individual per-repetition values and a standard
# deviation are included too, for anyone who wants to look past the
# average.
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
#   ./sweep_cpu_set_db.sh                        # TPCH_SF=1, REPS=5, default cpuset sweep
#   TPCH_SF=30 ./sweep_cpu_set_db.sh              # sweep CPU sets at SF30
#   REPS=10 ./sweep_cpu_set_db.sh "0" "0-3"       # 10 repetitions instead of 5

cd "$(dirname "$0")"

ENV_FILE="tpch_config.env"
PROFILE="duckdb-prebuilt"
TPCH_SF="${TPCH_SF:-1}"
REPS="${REPS:-5}"
# MOUNT_DIR must match docker-compose.yml's actual bind mount for
# duckdb-tpch-prebuilt exactly (./results/duckdb-prebuilt:/results) — the
# container always writes flat there, with no knowledge of TPCH_SF at
# all. RESULTS_DIR is where we organize things TO once files land in
# MOUNT_DIR; it's fine (and expected) for it to be a subdirectory of
# MOUNT_DIR — the file-only move logic below already ignores directories,
# so nesting doesn't cause re-moving on later runs.
MOUNT_DIR="results/duckdb-prebuilt"
RESULTS_DIR="results/duckdb-prebuilt/sf${TPCH_SF}"

CPU_SETS=("$@")
if [ ${#CPU_SETS[@]} -eq 0 ]; then
    #CPU_SETS=("0" "0-1" "0-3")
    CPU_SETS=("0" "0-1" "0-3" "0-7" "0-15" "0-31" "0-63" "0-127")
    #CPU_SETS=("0-7")
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
    echo "==> CPU_SET_DB=${cpu_set} (TPCH_SF=${TPCH_SF}, ${REPS} repetitions)"
    echo "=================================================="

    cpuset_dir="${RESULTS_DIR}/cpuset_$(sanitize "${cpu_set}")"
    mkdir -p "${cpuset_dir}"

    # Repetitions accumulate across separate invocations of this script,
    # for archival purposes — nothing here is ever deleted. Find the
    # highest existing rep_<N> already present (0 if none), and number
    # this invocation's new repetitions continuing from there, rather
    # than always starting at rep_1 and overwriting a previous run's
    # archived output.
    highest_existing=0
    for d in "${cpuset_dir}"/rep_*; do
        [ -d "$d" ] || continue
        n="${d##*/rep_}"
        case "$n" in
            ''|*[!0-9]*) continue ;;  # not a plain integer, skip
        esac
        if [ "$n" -gt "$highest_existing" ]; then
            highest_existing="$n"
        fi
    done
    if [ "${highest_existing}" -gt 0 ]; then
        echo "==> Found ${highest_existing} existing repetition(s) already archived for CPU_SET_DB=${cpu_set} — continuing from rep_$((highest_existing + 1))"
    fi

    for rep in $(seq "$((highest_existing + 1))" "$((highest_existing + REPS))"); do
        echo "--- Repetition ${rep} (this invocation: $((rep - highest_existing))/${REPS}) for CPU_SET_DB=${cpu_set} ---"

        echo "==> Building and running (CPU_SET_DB=${cpu_set}, TPCH_SF=${TPCH_SF}) ..."
        CPU_SET_DB="${cpu_set}" TPCH_SF="${TPCH_SF}" docker compose --env-file "${ENV_FILE}" --profile "${PROFILE}" up --build

        echo "==> Tearing down container and volume ..."
        docker compose --env-file "${ENV_FILE}" --profile "${PROFILE}" down -v

        rep_dir="${cpuset_dir}/rep_${rep}"
        mkdir -p "${rep_dir}"

        found_any=false
        for f in "${MOUNT_DIR}"/*; do
            base="$(basename "$f")"
            case "${base}" in
                sf*) continue ;;   # don't descend into our own organized subfolders
            esac
            if [ -f "$f" ]; then
                mv "$f" "${rep_dir}/"
                found_any=true
            fi
        done
        if [ "${found_any}" = "false" ]; then
            echo "!! No result files found directly under ${MOUNT_DIR} for CPU_SET_DB=${cpu_set} rep ${rep}" >&2
        fi
    done

    echo "==> Averaging all accumulated repetitions for CPU_SET_DB=${cpu_set} ..."
    python3 average_repetitions.py "${cpuset_dir}"

    echo "==> Done with CPU_SET_DB=${cpu_set}."
    echo
done

echo "All CPU sets complete (TPCH_SF=${TPCH_SF}, ${REPS} reps each). Results organized under ${RESULTS_DIR}/cpuset_<value>/"
