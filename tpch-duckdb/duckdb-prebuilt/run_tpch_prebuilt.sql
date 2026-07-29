-- TPC-H benchmark run for DuckDB, against a pre-generated database
-- instead of generating data via dbgen every run.
--
-- Uses DuckDB Labs' own pre-generated TPC-H database files
-- (https://blobs.duckdb.org/data/tpch-sf<N>.db, documented at
-- https://duckdb.org/docs/current/core_extensions/tpch), downloaded once
-- via download-data.sh rather than every container run — see
-- duckdb-prebuilt/Dockerfile for how TPCH_SF flows from
-- that download into the image. For scale factors with no pre-generated
-- file published, or if you want to sweep scale factors without a
-- rebuild each time, use the duckdb-tpch profile instead, which
-- generates data via dbgen and reads TPCH_SCALE_FACTOR at container
-- runtime.
--
-- Still needs INSTALL/LOAD tpch: that extension is what provides the
-- PRAGMA tpch(N) queries themselves, independent of how the base TPC-H
-- tables were populated — it doesn't need dbgen to have been called in
-- the same session, only for the standard-named tables to already exist
-- with the expected schema, which the pre-built file provides.
--
-- dbgen_start/dbgen_end below are kept as immediate, back-to-back
-- timestamps (so tpch_summary.json keeps the same schema as
-- duckdb/run_tpch.sql's output) even though no generation actually
-- happens here — dbgen_seconds will just read close to zero.
--
-- Latency/throughput measurement and JSON output are otherwise identical
-- to duckdb/run_tpch.sql — see that script's comments for the details.

INSTALL tpch;
LOAD tpch;

DROP TABLE IF EXISTS tpch_run_log;
CREATE TABLE tpch_run_log (event VARCHAR, ts TIMESTAMP);

.echo on
.timer on

INSERT INTO tpch_run_log VALUES ('dbgen_start', current_timestamp);
INSERT INTO tpch_run_log VALUES ('dbgen_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q1_start', current_timestamp);
PRAGMA tpch(1);
INSERT INTO tpch_run_log VALUES ('q1_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q2_start', current_timestamp);
PRAGMA tpch(2);
INSERT INTO tpch_run_log VALUES ('q2_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q3_start', current_timestamp);
PRAGMA tpch(3);
INSERT INTO tpch_run_log VALUES ('q3_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q4_start', current_timestamp);
PRAGMA tpch(4);
INSERT INTO tpch_run_log VALUES ('q4_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q5_start', current_timestamp);
PRAGMA tpch(5);
INSERT INTO tpch_run_log VALUES ('q5_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q6_start', current_timestamp);
PRAGMA tpch(6);
INSERT INTO tpch_run_log VALUES ('q6_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q7_start', current_timestamp);
PRAGMA tpch(7);
INSERT INTO tpch_run_log VALUES ('q7_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q8_start', current_timestamp);
PRAGMA tpch(8);
INSERT INTO tpch_run_log VALUES ('q8_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q9_start', current_timestamp);
PRAGMA tpch(9);
INSERT INTO tpch_run_log VALUES ('q9_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q10_start', current_timestamp);
PRAGMA tpch(10);
INSERT INTO tpch_run_log VALUES ('q10_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q11_start', current_timestamp);
PRAGMA tpch(11);
INSERT INTO tpch_run_log VALUES ('q11_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q12_start', current_timestamp);
PRAGMA tpch(12);
INSERT INTO tpch_run_log VALUES ('q12_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q13_start', current_timestamp);
PRAGMA tpch(13);
INSERT INTO tpch_run_log VALUES ('q13_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q14_start', current_timestamp);
PRAGMA tpch(14);
INSERT INTO tpch_run_log VALUES ('q14_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q15_start', current_timestamp);
PRAGMA tpch(15);
INSERT INTO tpch_run_log VALUES ('q15_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q16_start', current_timestamp);
PRAGMA tpch(16);
INSERT INTO tpch_run_log VALUES ('q16_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q17_start', current_timestamp);
PRAGMA tpch(17);
INSERT INTO tpch_run_log VALUES ('q17_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q18_start', current_timestamp);
PRAGMA tpch(18);
INSERT INTO tpch_run_log VALUES ('q18_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q19_start', current_timestamp);
PRAGMA tpch(19);
INSERT INTO tpch_run_log VALUES ('q19_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q20_start', current_timestamp);
PRAGMA tpch(20);
INSERT INTO tpch_run_log VALUES ('q20_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q21_start', current_timestamp);
PRAGMA tpch(21);
INSERT INTO tpch_run_log VALUES ('q21_end', current_timestamp);

INSERT INTO tpch_run_log VALUES ('q22_start', current_timestamp);
PRAGMA tpch(22);
INSERT INTO tpch_run_log VALUES ('q22_end', current_timestamp);

.timer off

-- Per-query latency (seconds), one JSON object per TPC-H query.
COPY (
    SELECT
        CAST(regexp_extract(s.event, '^q([0-9]+)_start$', 1) AS INTEGER) AS query_nr,
        epoch(e.ts) - epoch(s.ts) AS latency_seconds
    FROM tpch_run_log s
    JOIN tpch_run_log e ON e.event = replace(s.event, '_start', '_end')
    WHERE s.event LIKE 'q%_start'
    ORDER BY query_nr
) TO '/results/tpch_query_latency.json' (FORMAT JSON, ARRAY true);

-- Run summary: scale factor (from the image's baked-in value), ~zero
-- dbgen time (pre-built
-- data, nothing generated), total time to run all 22 queries
-- sequentially, and a simplified throughput figure.
COPY (
    WITH bounds AS (
        SELECT
            (SELECT ts FROM tpch_run_log WHERE event = 'dbgen_start') AS dbgen_start,
            (SELECT ts FROM tpch_run_log WHERE event = 'dbgen_end')   AS dbgen_end,
            (SELECT ts FROM tpch_run_log WHERE event = 'q1_start')    AS queries_start,
            (SELECT ts FROM tpch_run_log WHERE event = 'q22_end')     AS queries_end
    )
    SELECT
        getenv('TPCH_SF') AS scale_factor,
        22 AS num_queries,
        epoch(dbgen_end) - epoch(dbgen_start) AS dbgen_seconds,
        epoch(queries_end) - epoch(queries_start) AS total_query_seconds,
        22.0 / (epoch(queries_end) - epoch(queries_start)) AS queries_per_second,
        (22.0 / (epoch(queries_end) - epoch(queries_start))) * 3600 AS queries_per_hour
    FROM bounds
) TO '/results/tpch_summary.json' (FORMAT JSON, ARRAY true);
