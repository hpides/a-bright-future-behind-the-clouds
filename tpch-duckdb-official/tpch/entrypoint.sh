#!/bin/bash
set -euo pipefail

export SF="${TPCH_SCALE_FACTOR:-1}"
RESULTS_DIR="${RESULTS_DIR:-/results}"

# benchmark.py does `scale_factor_streams_map[scale_factor]`, a direct
# dictionary lookup against the exact scale factors defined in TPC-H spec
# section 5.3.4 — anything else KeyErrors deep inside the run. Validate
# up front with a clear message instead of letting that happen.
VALID_SCALE_FACTORS="1 10 20 30 100 300 1000 3000 10000"
valid=false
for v in ${VALID_SCALE_FACTORS}; do
    if [ "${SF}" = "${v}" ]; then
        valid=true
        break
    fi
done
if [ "${valid}" != "true" ]; then
    echo "!! TPCH_SCALE_FACTOR=${SF} is not supported by this harness." >&2
    echo "!! The official Throughput Test's required stream count is only" >&2
    echo "!! defined (TPC-H spec section 5.3.4) for these scale factors:" >&2
    echo "!!   ${VALID_SCALE_FACTORS}" >&2
    exit 1
fi

echo "==> TPC-H official Power/Throughput/Composite benchmark, scale factor ${SF}"
mkdir -p "${RESULTS_DIR}"

cd /bench

if [ ! -d "gen/sf${SF}" ] || [ "${FORCE_REGENERATE:-false}" = "true" ]; then
    echo "==> Generating TPC-H data + query streams + refresh sets (scale factor ${SF}) ..."
    echo "==> This runs the real dbgen/qgen — expect real time/disk usage at higher scale factors."
    ./generate.sh
else
    echo "==> Reusing existing data at gen/sf${SF} (set FORCE_REGENERATE=true to regenerate)"
fi

echo "==> Running the official Power/Throughput/Composite benchmark ..."
RUN_LOG="${RESULTS_DIR}/tpch_official_run.log"
python3 benchmark.py 2>&1 | tee "${RUN_LOG}"

echo "==> Extracting a structured JSON summary ..."
python3 - "${RUN_LOG}" "${RESULTS_DIR}/tpch_official_summary.json" "${SF}" << 'PYEOF'
import re
import json
import sys

run_log_path, summary_path, sf = sys.argv[1], sys.argv[2], sys.argv[3]
log = open(run_log_path).read()


def grab(pattern):
    m = re.search(pattern, log)
    return float(m.group(1)) if m else None


summary = {
    "scale_factor": int(sf),
    # benchmark.py's actual output is column-aligned with variable padding
    # (e.g. "tpch_power_at_size              = 130084.64"), not a single
    # space around "=" — \s* tolerates that instead of requiring an exact
    # single-space match.
    "load_time_seconds": grab(r"tpch_load_time\s*=\s*([\d.]+) seconds"),
    "power_total_queries_duration_seconds": grab(r"power_total_queries_duration\s*=\s*([\d.]+)"),
    "tpch_power_at_size": grab(r"tpch_power_at_size\s*=\s*([\d.]+)"),
    "throughput_measurement_interval_seconds": grab(r"throughput_measurement_interval\s*=\s*([\d.]+)"),
    "tpch_throughput_at_size": grab(r"tpch_throughput_at_size\s*=\s*([\d.]+)"),
    "tpch_qphh_at_size": grab(r"tpch_qphh_at_size\s*=\s*([\d.]+)"),
    "note": (
        "Not an official, audited TPC Benchmark Result. Per the TPC-H "
        "reference toolkit's EULA, do not present these figures as "
        "comparable to an official TPC Benchmark Result."
    ),
}

with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)

print(f"Wrote {summary_path}:")
print(json.dumps(summary, indent=2))
PYEOF

# benchmark.py's resource-utilization TSV (CPU/mem/disk over time) lands in
# the CWD (/bench) with a timestamped filename — copy the latest one out.
latest_tsv=$(ls -t /bench/log-sf"${SF}"-*.tsv 2>/dev/null | head -n1 || true)
if [ -n "${latest_tsv}" ]; then
    cp "${latest_tsv}" "${RESULTS_DIR}/"
    echo "==> Copied resource-utilization log: $(basename "${latest_tsv}")"
fi

echo "==> Done. Results in ${RESULTS_DIR}"
