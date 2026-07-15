-- TPC-H benchmark run for DuckDB.
--
-- Uses DuckDB's own built-in `tpch` extension (data generator + all 22
-- queries) rather than going through Benchbase — Benchbase has no DuckDB
-- connectivity at all (no DatabaseType, no driver), and TPC-C's OLTP-style
-- workload isn't a good fit for DuckDB anyway (see README). This runs
-- entirely in an in-memory database: it regenerates the dataset every run,
-- so there's nothing to persist between runs and no volume/permission
-- concerns for the database itself.
--
-- Scale factor comes from the TPCH_SCALE_FACTOR environment variable via
-- DuckDB's getenv() function (CLI-only).
--
-- Latency/throughput are measured with real wall-clock timestamps stored
-- in a table (tpch_run_log), not by parsing the CLI's `.timer` text — that
-- keeps the numbers exact regardless of output formatting, and lets us
-- compute them with plain SQL at the end. Two JSON files are written to
-- /results (bind-mounted from ./results/duckdb on the host) via DuckDB's
-- native `COPY ... TO ... (FORMAT JSON, ARRAY true)` — a plain SQL
-- statement, not a CLI-only dot-command, and ARRAY true gives a proper
-- single JSON array document rather than newline-delimited JSON:
--   tpch_query_latency.json - per-query wall-clock latency, in seconds
--   tpch_summary.json       - scale factor, total query time, and a
--                            simplified throughput figure (queries/sec,
--                            queries/hour). NOT the official TPC-H
--                            Composite Query-per-Hour (QphH) metric, which
--                            uses a geometric mean across a power test and
--                            a multi-stream throughput test — this is just
--                            query count divided by wall-clock time to run
--                            all 22 once, sequentially.
--
-- Query text/results and .timer progress still stream to stdout as before
-- (visible via `docker compose logs`); COPY writes the two files above
-- independently of whatever the CLI's own output mode is set to.

INSTALL tpch;
LOAD tpch;

CREATE TABLE tpch_run_log (event VARCHAR, ts TIMESTAMP);

.echo on
.timer on

INSERT INTO tpch_run_log VALUES ('dbgen_start', current_timestamp);
CALL dbgen(sf = getenv('TPCH_SCALE_FACTOR')::DOUBLE);
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

-- Run summary: scale factor, dataset generation time, total time to run
-- all 22 queries sequentially, and a simplified throughput figure.
COPY (
    WITH bounds AS (
        SELECT
            (SELECT ts FROM tpch_run_log WHERE event = 'dbgen_start') AS dbgen_start,
            (SELECT ts FROM tpch_run_log WHERE event = 'dbgen_end')   AS dbgen_end,
            (SELECT ts FROM tpch_run_log WHERE event = 'q1_start')    AS queries_start,
            (SELECT ts FROM tpch_run_log WHERE event = 'q22_end')     AS queries_end
    )
    SELECT
        getenv('TPCH_SCALE_FACTOR') AS scale_factor,
        22 AS num_queries,
        epoch(dbgen_end) - epoch(dbgen_start) AS dbgen_seconds,
        epoch(queries_end) - epoch(queries_start) AS total_query_seconds,
        22.0 / (epoch(queries_end) - epoch(queries_start)) AS queries_per_second,
        (22.0 / (epoch(queries_end) - epoch(queries_start))) * 3600 AS queries_per_hour
    FROM bounds
) TO '/results/tpch_summary.json' (FORMAT JSON, ARRAY true);
