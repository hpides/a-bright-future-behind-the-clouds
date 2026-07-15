#!/bin/bash
# Runs once, during the official postgres image's first-time initialization
# (docker-entrypoint-initdb.d), right after initdb generates the base
# postgresql.conf and before the real server starts listening. Appends an
# `include_if_exists` line pointing at our bind-mounted tuning.conf, rather
# than replacing postgresql.conf outright — replacing it risks silently
# losing settings the container needs to stay reachable at all (like
# listen_addresses='*', which initdb sets and a from-scratch file wouldn't
# unless you remembered to reproduce it). Postgres config files use
# last-value-wins semantics, so appending this after initdb's own content
# means tuning.conf's values take effect without touching anything else.
#
# Idempotent: only appends if not already present, so it's harmless if this
# somehow runs more than once against the same data directory. In practice
# docker-entrypoint-initdb.d scripts only run on first initialization of an
# empty PGDATA anyway — this persists in the postgres-data volume from then
# on.
#
# No shebang execute bit required: the official entrypoint sources *.sh
# files that aren't executable (falls back to `. "$f"`), so this works even
# if the executable bit doesn't survive a bind mount from the host.
set -euo pipefail

INCLUDE_LINE="include_if_exists '/etc/postgresql-custom/tuning.conf'"
CONF_FILE="${PGDATA}/postgresql.conf"

if grep -qF "${INCLUDE_LINE}" "${CONF_FILE}"; then
    echo "init-custom-config: tuning.conf already included in ${CONF_FILE} — skipping"
else
    {
        echo ""
        echo "# --- Added by init-custom-config.sh ---"
        echo "# Layers postgres/tuning.conf on top of the settings above. Since"
        echo "# Postgres config parsing uses last-value-wins, this overrides only"
        echo "# the parameters tuning.conf actually sets; everything else (e.g."
        echo "# listen_addresses, unix socket dir) stays exactly as initdb left it."
        echo "${INCLUDE_LINE}"
    } >> "${CONF_FILE}"
    echo "init-custom-config: appended tuning.conf include to ${CONF_FILE}"
fi
