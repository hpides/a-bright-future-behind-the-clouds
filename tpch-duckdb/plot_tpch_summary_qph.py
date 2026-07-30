#!/usr/bin/env python3
"""
Plots scale factor vs. queries-per-hour from one or more tpch_summary.json
files produced by the duckdb-tpch profile's run_tpch.sql.

Handles the case where each scale-factor run's results live in its own
folder with the same filename, e.g.:

    results/duckdb/sf1/tpch_summary.json
    results/duckdb/sf5/tpch_summary.json
    results/duckdb/sf10/tpch_summary.json
    results/duckdb/sf20/tpch_summary.json

scale_factor is read from each file's own JSON content (not parsed from the
folder name), so this works regardless of how the folders happen to be
named. Each tpch_summary.json is a JSON array (per COPY ... FORMAT JSON,
ARRAY true); this script also tolerates a file containing more than one
entry, in case results are ever consolidated into a single file instead.

Usage:
    python3 plot_tpch_summary_qph.py
    python3 plot_tpch_summary_qph.py --glob "results/duckdb/sf*/tpch_summary.json"
    python3 plot_tpch_summary_qph.py --glob "some/other/pattern/*.json" --output out.png
    python3 plot_tpch_summary_qph.py --log-x
"""

import argparse
import glob
import json
import sys

import matplotlib.pyplot as plt


def load_entries(pattern: str) -> list[dict]:
    """Reads every JSON file matching `pattern` and collects all summary
    entries found across all of them. Each file is expected to contain a
    JSON array of one or more summary objects (as written by
    duckdb/run_tpch.sql's COPY ... FORMAT JSON, ARRAY true)."""
    paths = sorted(glob.glob(pattern, recursive=True))
    if not paths:
        print(f"No files matched pattern: {pattern!r}", file=sys.stderr)
        sys.exit(1)

    entries = []
    for path in paths:
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"!! Skipping {path}: {e}", file=sys.stderr)
            continue

        # Each file is a JSON array; tolerate a bare object too, just in case.
        rows = data if isinstance(data, list) else [data]
        for row in rows:
            if "scale_factor" not in row or "queries_per_hour" not in row:
                print(f"!! Skipping an entry in {path}: missing expected fields", file=sys.stderr)
                continue
            entries.append(
                {
                    "scale_factor": float(row["scale_factor"]),
                    "queries_per_hour": float(row["queries_per_hour"]),
                    "source": path,
                }
            )

    if not entries:
        print("No usable entries found in any matched file.", file=sys.stderr)
        sys.exit(1)

    return sorted(entries, key=lambda e: e["scale_factor"])


def plot(entries: list[dict], output: str, log_x: bool) -> None:
    scale_factors = [e["scale_factor"] for e in entries]
    qph = [e["queries_per_hour"] for e in entries]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(scale_factors, qph, marker="o", linewidth=2, markersize=7, color="tab:orange")

    for sf, q in zip(scale_factors, qph):
        ax.annotate(
            f"{q:,.0f}",
            (sf, q),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
        )

    if log_x:
        ax.set_xscale("log")
    ax.set_xlabel("TPC-H Scale Factor")
    ax.set_ylabel("Queries per Hour")
    ax.set_title("DuckDB TPC-H: Queries per Hour by Scale Factor")
    ax.grid(True, alpha=0.3)
    ax.set_xticks(scale_factors)
    ax.set_xticklabels([str(int(sf)) if sf == int(sf) else str(sf) for sf in scale_factors])
    ax.get_yaxis().set_major_formatter(plt.matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    print(f"Wrote {output}")

    print("\nData plotted:")
    for e in entries:
        print(f"  scale_factor={e['scale_factor']:<8g} queries_per_hour={e['queries_per_hour']:<12,.1f} ({e['source']})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--glob",
        default="results/duckdb/sf*/tpch_summary.json",
        help="Glob pattern matching tpch_summary.json files (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default="tpch_qph_by_scale_factor.png",
        help="Output image path (default: %(default)s)",
    )
    parser.add_argument(
        "--log-x",
        action="store_true",
        help="Use a log scale on the x-axis (useful if scale factors span orders of magnitude)",
    )
    args = parser.parse_args()

    entries = load_entries(args.glob)
    plot(entries, args.output, args.log_x)


if __name__ == "__main__":
    main()
