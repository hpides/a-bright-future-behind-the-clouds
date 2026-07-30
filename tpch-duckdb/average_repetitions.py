#!/usr/bin/env python3
"""
Averages queries_per_second/queries_per_hour across every rep_<N>
repetition folder found under a cpuset run directory, produced by
sweep_cpu_set_db.sh as <cpuset_dir>/rep_1/tpch_summary.json, rep_2/, etc.

Repetitions accumulate across separate invocations of the sweep script
(nothing is ever deleted, for archival purposes) — so rather than taking
an exact expected count, this globs for whatever rep_* folders actually
exist and averages over all of them. Run the sweep script twice and
there'll be more repetitions to average over the second time, not a
reset back to the first invocation's count.

Writes <cpuset_dir>/tpch_summary.json in the same schema tpch_summary.json
normally has (so the plotting scripts need no changes at all — they just
see one, now-averaged, summary per cpuset folder) — with
queries_per_second/queries_per_hour replaced by the arithmetic mean across
repetitions, plus num_repetitions, queries_per_second_stdev, and
queries_per_second_individual for anyone who wants to look past the
average.

Usage:
    python3 average_repetitions.py <cpuset_dir>
    python3 average_repetitions.py results/duckdb-prebuilt/sf1/cpuset_0
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

REP_DIR_RE = re.compile(r"^rep_(\d+)$")


def average_repetitions(cpuset_dir: Path) -> dict:
    rep_dirs = sorted(
        (d for d in cpuset_dir.iterdir() if d.is_dir() and REP_DIR_RE.match(d.name)),
        key=lambda d: int(REP_DIR_RE.match(d.name).group(1)),
    )

    qps_values = []
    qph_values = []
    last_row = None

    for rep_dir in rep_dirs:
        summary_path = rep_dir / "tpch_summary.json"
        if not summary_path.exists():
            print(f"!! Missing {summary_path}, excluding from average", file=sys.stderr)
            continue
        with open(summary_path) as f:
            data = json.load(f)
        row = data[0] if isinstance(data, list) else data
        qps_values.append(float(row["queries_per_second"]))
        qph_values.append(float(row["queries_per_hour"]))
        last_row = row

    if not qps_values:
        print(f"!! No usable rep_* repetitions found under {cpuset_dir} — cannot compute an average", file=sys.stderr)
        sys.exit(1)

    avg_qps = statistics.mean(qps_values)
    avg_qph = statistics.mean(qph_values)
    stdev_qps = statistics.stdev(qps_values) if len(qps_values) > 1 else 0.0

    summary = dict(last_row)
    summary["queries_per_second"] = avg_qps
    summary["queries_per_hour"] = avg_qph
    summary["num_repetitions"] = len(qps_values)
    summary["queries_per_second_stdev"] = stdev_qps
    summary["queries_per_second_individual"] = qps_values

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cpuset_dir", type=Path, help="Directory containing rep_1/, rep_2/, ... subfolders")
    args = parser.parse_args()

    summary = average_repetitions(args.cpuset_dir)

    output_path = args.cpuset_dir / "tpch_summary.json"
    with open(output_path, "w") as f:
        json.dump([summary], f, indent=2)

    print(f"Average queries_per_second over {summary['num_repetitions']} accumulated reps: "
          f"{summary['queries_per_second']:.3f} (stdev {summary['queries_per_second_stdev']:.3f})")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
