#!/bin/bash
set -euo pipefail

# Downloads DuckDB Labs' pre-generated TPC-H database at a given scale
# factor once, into this service's own build context
# (duckdb-prebuilt/data/tpch-sf<N>.db), so the Dockerfile can just COPY an
# already-local file rather than fetching it during the Docker build
# itself. Run this once before building; re-run any time to refresh a
# given scale factor's file — it's idempotent per scale factor, skipping
# the download entirely if that scale factor's file already exists.
#
# Source: https://blobs.duckdb.org/data/tpch-sf<N>.db, documented at
# https://duckdb.org/docs/current/core_extensions/tpch as an official,
# pre-generated convenience artifact from DuckDB Labs. Only these scale
# factors have a pre-generated file actually published — anything else
# will fail with a clear error rather than a confusing download failure:
VALID_SCALE_FACTORS="1 3 10 30 100 300 1000 3000 10000"
#
# Usage:
#   ./download-data.sh                 # TPCH_SF env var, or 1
#   ./download-data.sh 30              # explicit scale factor
#   ./download-data.sh 30 --force      # re-download even if already present
#   ./download-data.sh --force         # re-download at the resolved default SF

cd "$(dirname "$0")"

SF="${TPCH_SF:-1}"
FORCE="false"
for arg in "$@"; do
    case "${arg}" in
        --force) FORCE="true" ;;
        *) SF="${arg}" ;;
    esac
done

valid=false
for v in ${VALID_SCALE_FACTORS}; do
    if [ "${SF}" = "${v}" ]; then
        valid=true
        break
    fi
done
if [ "${valid}" != "true" ]; then
    echo "!! Scale factor '${SF}' has no pre-generated file published." >&2
    echo "!! Available: ${VALID_SCALE_FACTORS}" >&2
    exit 1
fi

DATA_DIR="/data_nvme/itolovski/data"
DATA_FILE="${DATA_DIR}/tpch-sf${SF}.db"
URL="https://blobs.duckdb.org/data/tpch-sf${SF}.db"

mkdir -p "${DATA_DIR}"

if [ -s "${DATA_FILE}" ]; then
    echo "==> ${DATA_FILE} already exists ($(du -h "${DATA_FILE}" | cut -f1)) — skipping download."
    echo "==> Delete it first (or pass --force) if you want to re-download."
    if [ "${FORCE}" != "true" ]; then
        exit 0
    fi
    echo "==> --force given, re-downloading anyway."
fi

echo "==> Downloading ${URL} ..."
if command -v curl >/dev/null 2>&1; then
    curl -fSL --progress-bar -o "${DATA_FILE}.tmp" "${URL}"
elif command -v wget >/dev/null 2>&1; then
    wget -O "${DATA_FILE}.tmp" "${URL}"
else
    echo "!! Neither curl nor wget is available. Install one and re-run." >&2
    exit 1
fi


size=$(stat -c%s "${DATA_FILE}.tmp" 2>/dev/null || stat -f%z "${DATA_FILE}.tmp")
if [ "${size}" -lt 1000000 ]; then
    echo "!! Downloaded file is suspiciously small (${size} bytes) — not replacing" >&2
    echo "!! any existing ${DATA_FILE}. Check the URL/network and try again." >&2
    rm -f "${DATA_FILE}.tmp"
    exit 1
fi

mv "${DATA_FILE}.tmp" "${DATA_FILE}"
echo "==> Done: ${DATA_FILE} ($(du -h "${DATA_FILE}" | cut -f1))"
echo "==> Now run: TPCH_SF=${SF} docker compose --env-file tpch_config.env --profile duckdb-prebuilt build"
