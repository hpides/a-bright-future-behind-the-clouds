import math
import os
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import LogLocator

usetex = True
rc = {
    "font.family": "serif",
    "font.serif": ["Linux Libertine O", "Linux Libertine",
                   "Libertinus Serif", "DejaVu Serif"],
    "font.size": 21,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
}
if usetex:
    rc.update({
        "text.usetex": True,
        "font.size": 21,
        "text.latex.preamble": r"\usepackage[T1]{fontenc}"
                               r"\usepackage[libertine]{libertine}",
    })
matplotlib.rcParams.update(rc)

# ---------------------------------------------------------------------------
# Data layout: DATA_ROOT/<machine>/postgres/sf<X>.samples.csv
# Only postgres is read; each file is a BenchBase samples.csv covering every
# terminal-count phase for that (machine, scale factor) run, back to back.
# ---------------------------------------------------------------------------
DATA_ROOT = os.path.join(os.path.dirname(__file__), "results")
OUT_PATH = os.path.join(os.path.dirname(__file__), "tpcc_scalability_combined_subplots.png")
OUT_PATH = os.path.join(os.path.dirname(__file__), "tpcc_scalability_combined_subplots.svg")
SCALE_FACTORS = [10, 50, 100, 250, 500]  # warehouses
DATABASE = "postgres"

MACHINES = {
    "pi5":     {"label": "Raspberry Pi 5",       "color": "#e6194b", "marker": "o", "linestyle": "-"},
    "m1-max":  {"label": "Apple M1 Pro",         "color": "#f58231", "marker": "v", "linestyle": (0, (3, 1, 1, 1))},
    "m4-max":  {"label": "Apple M4 Max",         "color": "#3cb44b", "marker": "s", "linestyle": "--"},
    "zen2":    {"label": "AMD EPYC (Zen 2)",     "color": "#911eb4", "marker": "D", "linestyle": "-."},
    "zen5":    {"label": "AMD EPYC (Zen 5)",     "color": "#4363d8", "marker": "^", "linestyle": ":"},
}

THRESHOLDS = {
    "Tx Small": {"value": 175,   "color": "black", "marker": "x", "linestyle": (0, (1, 1))},
    "Tx Medium": {"value": 875,   "color": "black", "marker": "+", "linestyle": (0, (5, 1))},
    "Tx Large": {"value": 17500, "color": "black", "marker": "*", "linestyle": (0, (3, 3))},
}

# ---------------------------------------------------------------------------
# Terminal-count phases. BenchBase does NOT emit samples during <warmup> --
# only during the measured <time> -- so phase windows in samples.csv are
# simply back-to-back blocks of `time` seconds. Edit TERMINALS/PHASE_SECONDS
# (or give each phase its own duration in PHASES) to match your BenchBase
# <works> config.
# ---------------------------------------------------------------------------
TERMINALS = [1, 2, 4, 8, 16, 32, 64]
PHASE_SECONDS = 60
PHASES = [(t, PHASE_SECONDS) for t in TERMINALS]  # [(terminals, time), ...]

TIME_COL_CANDIDATES = ["Time (seconds)", "time", "Time", "elapsed_sec", "second"]
THROUGHPUT_COL_CANDIDATES = [
    "Throughput (requests/second)",
    "throughput",
    "Throughput",
    "tps",
]


def compute_phase_windows(phases):
    """Back-to-back [start, end) windows, one per phase, in samples.csv time."""
    windows = []
    cursor = 0.0
    for terminals, time in phases:
        start = cursor
        end = start + time
        windows.append({"terminals": terminals, "start": start, "end": end})
        cursor = end
    return windows


def find_column(df, candidates, kind):
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(
        f"Could not find a {kind} column in columns {list(df.columns)}. "
        f"Tried: {candidates}."
    )


def average_throughput_per_phase(csv_path, windows):
    """Return {terminals: mean_throughput} for one samples.csv file."""
    df = pd.read_csv(csv_path)
    time_col = find_column(df, TIME_COL_CANDIDATES, "time")
    throughput_col = find_column(df, THROUGHPUT_COL_CANDIDATES, "throughput")

    result = {}
    for w in windows:
        mask = (df[time_col] >= w["start"]) & (df[time_col] < w["end"])
        subset = df.loc[mask, throughput_col]
        if subset.empty:
            print(
                f"  warning: no samples in {os.path.basename(csv_path)} for "
                f"terminals={w['terminals']} (check PHASES matches this run's config)"
            )
            continue
        result[w["terminals"]] = subset.mean()
    return result


windows = compute_phase_windows(PHASES)
THREAD_TO_IDX = {t: i for i, t in enumerate(TERMINALS)}

# --- Pass 1: load everything first so we can compute a shared y-range -----
# results_by_sf[sf][machine] = (terminals_list, throughput_list)
results_by_sf = {sf: {} for sf in SCALE_FACTORS}
all_values = []
for sf in SCALE_FACTORS:
    for machine in MACHINES:
        csv_path = os.path.join(DATA_ROOT, machine, DATABASE, f"sf{sf}.samples.csv")
        if not os.path.isfile(csv_path):
            continue
        per_terminal = average_throughput_per_phase(csv_path, windows)
        points = sorted(per_terminal.items())
        if not points:
            continue
        terminals, ys = zip(*points)
        results_by_sf[sf][machine] = (terminals, ys)
        all_values.extend(ys)
        all_values.extend(spec["value"] for spec in THRESHOLDS.values())

y_bottom = 10
y_top = 10 ** math.ceil(math.log10(max(all_values)))

ncols = len(SCALE_FACTORS)
nrows = 1
last_row_count = len(SCALE_FACTORS) - (nrows - 1) * ncols

fig = plt.figure(figsize=(4.0 * ncols, 3.0 * nrows))
gs = fig.add_gridspec(nrows, ncols * 2)

axes = []
for idx in range(len(SCALE_FACTORS)):
    row = idx // ncols
    col_in_row = idx % ncols
    if row == nrows - 1 and last_row_count < ncols:
        left_pad = ncols - last_row_count
        col_start = left_pad + col_in_row * 2
    else:
        col_start = col_in_row * 2
    axes.append(fig.add_subplot(gs[row, col_start:col_start + 2]))

# --- Pass 2: plot using the precomputed data and shared y-range -----------
for idx, (ax, sf) in enumerate(zip(axes, SCALE_FACTORS)):
    for machine, style in MACHINES.items():
        if machine not in results_by_sf[sf]:
            continue
        terminals, ys = results_by_sf[sf][machine]
        xs = [THREAD_TO_IDX[t] for t in terminals]
        ax.plot(xs, ys, label=style["label"], color=style["color"],
                marker=style["marker"], linestyle=style["linestyle"],
                markersize=7, linewidth=2)

    for label, spec in THRESHOLDS.items():
        ax.axhline(spec["value"], color=spec["color"], linestyle=spec["linestyle"],
                   marker=spec["marker"], markersize=8, linewidth=1.5, label=label)

    ax.set_xticks(range(len(TERMINALS)))
    ax.set_xticklabels([str(t) for t in TERMINALS])
    ax.set_xlabel(rf"\# Terminals", fontsize=19)
    if idx % ncols == 0:
        # Only the leftmost subplot in each row gets a y-axis label.
        ax.set_ylabel("Throughput (log) [Tx/s]", fontsize=17)
    ax.set_title(rf"\#warehouses = {sf}", fontsize=17)
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, which="major", linestyle="--", alpha=0.5)
    ax.set_yscale("log")
    # Log-aware tick locator: major ticks ONLY at whole powers of 10 (subs
    # fixed to (1.0,) so matplotlib never injects odd "2x10^n" ticks), minor
    # ticks at 2x/5x within each decade for finer unlabeled gridlines.
    ax.yaxis.set_major_locator(LogLocator(base=10.0, subs=(1.0,), numticks=15))
    ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=(0.2, 0.5, 2, 5), numticks=15))
    ax.set_ylim(bottom=y_bottom, top=y_top)  # same range on every subplot
    ax.set_xlim(left=-0.5, right=len(TERMINALS) - 0.5)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles, labels,
    loc="lower center",
    bbox_to_anchor=(0.5, 1.0),
    ncol=len(MACHINES) + len(THRESHOLDS),
    fontsize=19,
    borderaxespad=0,
    columnspacing=1.0,
    handletextpad=0.4,
    handlelength=1.5,
)

fig.tight_layout(pad=0.3, rect=[0, 0, 1, 1.0])
fig.savefig(OUT_PATH, bbox_inches="tight")
print(f"Saved to {OUT_PATH}")