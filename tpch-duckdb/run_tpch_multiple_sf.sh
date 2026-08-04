#!/bin/bash
set -uo pipefail
# Deliberately NOT using -e (errexit) at this level — a failed sweep is
# handled explicitly via if/else below, letting the script continue to
# the next scale factor rather than aborting the whole run. -u and
# pipefail stay on to catch genuine bugs (unset vars, broken pipes) in
# this wrapper itself.

# Runs run_tpch_cpu_sets_5_runs.sh once per scale factor, one after another. If
# one scale factor's sweep fails, the next one still runs — failures are
# recorded and reported in a summary at the end rather than aborting the
# whole script partway through.
#
# Usage:
#   ./run_two_sf_sweeps.sh              # defaults to TPCH_SF 1 and 30
#   ./run_two_sf_sweeps.sh 1 100        # or pass your own scale factors
#
# CPU sets and REPS are controlled the same way as always — this script
# just varies TPCH_SF across separate run_tpch_cpu_sets_5_runs.sh invocations. To
# use non-default cpuset values, edit run_tpch_cpu_sets_5_runs.sh's own defaults
# or export REPS before running this, same as running run_tpch_cpu_sets_5_runs.sh
# directly.

cd "$(dirname "$0")"

SCALE_FACTORS=("$@")
if [ ${#SCALE_FACTORS[@]} -eq 0 ]; then
    SCALE_FACTORS=(1 10 30 100 300)
fi

declare -A RESULTS

for sf in "${SCALE_FACTORS[@]}"; do
    echo "###########################################################"
    echo "### Running run_tpch_cpu_sets_5_runs.sh at TPCH_SF=${sf}"
    echo "###########################################################"

    if TPCH_SF="${sf}" ./run_tpch_cpu_sets_5_runs.sh; then
        RESULTS["${sf}"]="SUCCESS"
        echo "==> Sweep at TPCH_SF=${sf} completed successfully."
    else
        exit_code=$?
        RESULTS["${sf}"]="FAILED (exit code ${exit_code})"
        echo "!! Sweep at TPCH_SF=${sf} FAILED (exit code ${exit_code}) — continuing to next scale factor." >&2
    fi
    echo
done

echo "###########################################################"
echo "### Summary"
echo "###########################################################"
overall_failed=false
for sf in "${SCALE_FACTORS[@]}"; do
    echo "  TPCH_SF=${sf}: ${RESULTS[${sf}]}"
    case "${RESULTS[${sf}]}" in
        SUCCESS) ;;
        *) overall_failed=true ;;
    esac
done

if [ "${overall_failed}" = "true" ]; then
    echo
    echo "!! At least one scale factor's sweep failed — see above for details." >&2
    exit 1
fi

echo
echo "All scale factors completed successfully."
