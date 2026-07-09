# syntax=docker/dockerfile:1

#############################################
# Stage 1: build Benchbase (postgres profile)
#############################################
# Benchbase currently requires JDK 23 to compile.
FROM eclipse-temurin:23-jdk AS build

# Use CedarDB's own Benchbase fork, not upstream cmu-db/benchbase.
# It adds a dedicated CEDARDB DatabaseType with its own ddl-cedardb.sql and
# dialect-cedardb.xml for tpcc/chbenchmark — needed because CedarDB differs
# from Postgres in small but real ways (e.g. no CASCADE on DROP TABLE, and a
# tweaked NewOrder query dialect). Using plain type=POSTGRES against upstream
# Benchbase will fail schema creation on CedarDB.
ARG BENCHBASE_REPO=https://github.com/cedardb/benchbase.git
ARG BENCHBASE_REF=main

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Still uses the "postgres" Maven profile to pull in the org.postgresql JDBC
# driver, since CedarDB speaks the Postgres wire protocol — the profile only
# controls which JDBC driver dependency gets bundled, not the SQL dialect/DDL,
# which come from the CEDARDB DatabaseType added by this fork.
RUN git clone --depth 1 --branch "${BENCHBASE_REF}" "${BENCHBASE_REPO}" .

RUN ./mvnw -B clean package -P postgres -DskipTests \
    && mkdir -p /opt/benchbase \
    && tar --strip-components=1 -xzf target/benchbase-postgres.tgz -C /opt/benchbase

#############################################
# Stage 2: slim runtime image
#############################################
FROM eclipse-temurin:23-jre

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client gettext-base \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash benchbase

WORKDIR /benchbase

COPY --from=build /opt/benchbase/ /benchbase/

# Single TPC-C config template, parameterized by DB_TYPE/DB_ISOLATION as well
# as connection details — the entrypoint fills these in based on DB_ENGINE.
COPY config/tpcc_config.xml /benchbase/config/tpcc_config.xml
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh \
    && chmod -R a+rX /benchbase

# Container starts as root (default, no USER here) so the entrypoint can fix
# permissions on the bind-mounted results directory — Docker creates that
# mount as root:root if it doesn't already exist on the host, and only root
# (or the owner) can chmod it. The entrypoint drops privileges to the
# unprivileged "benchbase" user before actually running Benchbase.

# Sensible defaults for connection/tuning details; override with
# `docker run -e ...` or docker-compose. DB_ENGINE has deliberately NO
# default here — it must be set explicitly to "cedardb" or "postgres",
# or the entrypoint refuses to start.
ENV DB_HOST=cedardb \
    DB_PORT=5432 \
    DB_NAME=benchbase \
    DB_USER=admin \
    DB_PASSWORD=password \
    TPCC_WAREHOUSES=10 \
    TPCC_TERMINALS=4 \
    TPCC_DURATION_SEC=60 \
    BENCHBASE_CREATE=true \
    BENCHBASE_LOAD=true \
    BENCHBASE_EXECUTE=true \
    RESULTS_DIR=/benchbase/results

# Invoked via bash explicitly (rather than relying on the executable bit /
# shebang) so this can't fail with "Permission denied" even if the execute
# bit gets lost somewhere in the build context / cache.
ENTRYPOINT ["/bin/bash", "/usr/local/bin/entrypoint.sh"]
