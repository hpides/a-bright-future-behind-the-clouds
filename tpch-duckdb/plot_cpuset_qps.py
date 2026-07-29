#!/usr/bin/env python3
"""
Plots CPU core count (from CPU_SET_DB) vs. queries-per-second from one or
more tpch_summary.json files produced by sweep_cpu_set_db.sh, e.g.:

    results/duckdb-prebuilt/sf1/cpuset_0/tpch_summary.json
    results/duckdb-prebuilt/sf1/cpuset_0-3/tpch_summary.json
    results/duckdb-prebuilt/sf1/cpuset_0,2,4,6/tpch_summary.json
    results/duckdb-prebuilt/sf1/cpuset_0-7/tpch_summary.json

Unlike the scale-factor version of this script, the swept variable here
(the cpuset value) is NOT a field inside tpch_summary.json — it only
exists in the folder name, so it's parsed from there instead. Since
cpuset strings ("0-3", "0,2,4,6") aren't simple numbers, each one is
parsed into an actual CPU core count for meaningful x-axis ordering
(e.g. "0-3" -> 4 cores), while the real cpuset string is still shown as
the axis tick label so it stays readable.

--scale-factor selects which sf<N> folder to plot (results are organized
per scale factor by sweep_cpu_set_db.sh, since CPU_SET_DB sweeps are run
at one fixed scale factor at a time) — it only affects the *default*
glob pattern; passing --glob explicitly overrides it entirely, e.g. if
you organize results differently.

Usage:
    python3 plot_cpuset_qps.py                          # scale factor 1 (default)
    python3 plot_cpuset_qps.py --scale-factor 30
    python3 plot_cpuset_qps.py --glob "some/other/pattern/cpuset_*/tpch_summary.json"
    python3 plot_cpuset_qps.py --scale-factor 30 --output out.png
"""

import argparse
import glob
import json
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt

CPUSET_DIR_RE = re.compile(r"^cpuset_(.+)$")


def cpuset_core_count(cpuset: str) -> int:
    """Parses a Docker --cpuset-cpus style string ("0", "0-3", "0,2,4,6",
    "0-3,8-11") into the number of CPU cores it covers."""
    count = 0
    for segment in cpuset.split(","):
        segment = segment.strip()
        if not segment:
            continue
        if "-" in segment:
            start, end = segment.split("-", 1)
            count += int(end) - int(start) + 1
        else:
            count += 1
    return count


def load_entries(pattern: str) -> list[dict]:
    """Reads every JSON file matching `pattern`, pairing each with the
    cpuset value parsed from its parent folder's name (cpuset_<value>)."""
    paths = sorted(glob.glob(pattern, recursive=True))
    if not paths:
        print(f"No files matched pattern: {pattern!r}", file=sys.stderr)
        sys.exit(1)

    entries = []
    for path in paths:
        parent_name = Path(path).parent.name
        m = CPUSET_DIR_RE.match(parent_name)
        if not m:
            print(f"!! Skipping {path}: parent folder {parent_name!r} doesn't match cpuset_<value>", file=sys.stderr)
            continue
        cpuset = m.group(1)

        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"!! Skipping {path}: {e}", file=sys.stderr)
            continue

        rows = data if isinstance(data, list) else [data]
        for row in rows:
            if "queries_per_second" not in row:
                print(f"!! Skipping an entry in {path}: missing queries_per_second", file=sys.stderr)
                continue
            try:
                cores = cpuset_core_count(cpuset)
            except ValueError:
                print(f"!! Skipping {path}: couldn't parse cpuset {cpuset!r}", file=sys.stderr)
                continue
            entries.append(
                {
                    "cpuset": cpuset,
                    "cores": cores,
                    "queries_per_second": float(row["queries_per_second"]),
                    "source": path,
                }
            )

    if not entries:
        print("No usable entries found in any matched file.", file=sys.stderr)
        sys.exit(1)

    return sorted(entries, key=lambda e: (e["cores"], e["cpuset"]))


def plot(entries: list[dict], output: str) -> None:
    x_positions = list(range(len(entries)))
    qps = [e["queries_per_second"] for e in entries]
    labels = [f'{e["cpuset"]}\n({e["cores"]} cores)' for e in entries]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x_positions, qps, marker="o", linewidth=2, markersize=7)

    for x, q in zip(x_positions, qps):
        ax.annotate(
            f"{q:.1f}",
            (x, q),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
        )

    ax.set_xlabel("CPU_SET_DB")
    ax.set_ylabel("Queries per Second")
    ax.set_title("DuckDB TPC-H: Queries per Second by CPU Set")
    ax.grid(True, alpha=0.3)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    print(f"Wrote {output}")

    print("\nData plotted:")
    for e in entries:
        print(f"  cpuset={e['cpuset']:<12} cores={e['cores']:<4} queries_per_second={e['queries_per_second']:<10.3f} ({e['source']})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--scale-factor",
        default="1",
        help="Which sf<N> folder to plot (default: %(default)s). Only affects the default --glob.",
    )
    parser.add_argument(
        "--glob",
        default=None,
        help="Glob pattern matching tpch_summary.json files "
        "(default: results/duckdb-prebuilt/sf<scale-factor>/cpuset_*/tpch_summary.json)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output image path (default: tpch_qps_by_cpuset_sf<scale-factor>.png)",
    )
    args = parser.parse_args()

    pattern = args.glob or f"results/duckdb-prebuilt/sf{args.scale_factor}/cpuset_*/tpch_summary.json"
    output = args.output or f"tpch_qps_by_cpuset_sf{args.scale_factor}.png"

    entries = load_entries(pattern)
    plot(entries, output)


if __name__ == "__main__":
    main()
