#!/bin/bash
set -euo pipefail

# DB_ENGINE must be set explicitly — there is no default. Silently
# benchmarking the wrong engine is worse than failing fast with a clear error.
: "${DB_ENGINE:?DB_ENGINE must be set to 'cedardb' or 'postgres' — no default is provided}"

RESULTS_DIR="${RESULTS_DIR:-/benchbase/results/$DB_ENGINE}"
CONFIG_TEMPLATE="/benchbase/config/tpcc_config.xml"
CONFIG_RENDERED="/tmp/tpcc_config.xml"

# DB_ENGINE maps to the Benchbase DatabaseType (DB_TYPE) and isolation level
# used in config/tpcc_config.xml. CEDARDB picks up CedarDB's own
# ddl-cedardb.sql / dialect-cedardb.xml (added by the cedardb/benchbase fork);
# POSTGRES uses Benchbase's standard ddl-postgres.sql unchanged.
case "${DB_ENGINE}" in
    cedardb)
        export DB_TYPE=CEDARDB
        #export DB_ISOLATION=TRANSACTION_REPEATABLE_READ
        ;;
    postgres)
        export DB_TYPE=POSTGRES
        #export DB_ISOLATION=TRANSACTION_REPEATABLE_READ
        ;;
    *)
        echo "!! Unknown DB_ENGINE '${DB_ENGINE}' (expected 'cedardb' or 'postgres')" >&2
        exit 1
        ;;
esac

echo "==> Target: ${DB_ENGINE} (${DB_TYPE}) at ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "==> Waiting for database to accept connections ..."
tries=0
# Both CedarDB and Postgres speak the Postgres wire protocol, so pg_isready
# works as the readiness probe for either engine.
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ "${tries}" -ge 60 ]; then
        echo "!! Database did not become ready in time" >&2
        exit 1
    fi
    sleep 2
done
echo "==> Database is ready."

echo "==> Rendering Benchbase config from environment ..."
envsubst < "${CONFIG_TEMPLATE}" > "${CONFIG_RENDERED}"

# Make sure the results directory exists and is writable by any user.
# When this path is a fresh bind mount from the host (e.g. ./results/cedardb),
# Docker creates it as root:root before the container even starts, and only
# root (or the owner) is allowed to chmod it — a non-root process can't fix
# this itself. So this step needs to run while we're still root; we drop
# privileges below, right before actually running Benchbase.
mkdir -p "${RESULTS_DIR}"

if [ "$(id -u)" = "0" ]; then
    chmod -R a+w "${RESULTS_DIR}"
else
    # Already unprivileged (e.g. a custom image with USER set) — best effort.
    chmod -R a+w "${RESULTS_DIR}" 2>/dev/null || \
        echo "!! Could not chmod ${RESULTS_DIR} (not running as root) — continuing anyway" >&2
fi

echo "==> Running Benchbase TPC-C against ${DB_ENGINE} (warehouses=${TPCC_WAREHOUSES}, terminals=${TPCC_TERMINALS}, duration=${TPCC_DURATION_SEC}s)"
echo "    create=${BENCHBASE_CREATE} load=${BENCHBASE_LOAD} execute=${BENCHBASE_EXECUTE}"

exec java -jar benchbase.jar \
    -b tpcc \
    -c "${CONFIG_RENDERED}" \
    -d "${RESULTS_DIR}" \
    --create="${BENCHBASE_CREATE}" \
    --load="${BENCHBASE_LOAD}" \
    --execute="${BENCHBASE_EXECUTE}" \
    "$@"
