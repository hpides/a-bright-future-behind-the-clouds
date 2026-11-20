import json
import os
import re
import matplotlib
import matplotlib.pyplot as plt

usetex=True
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

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
#OUT_PATH = os.path.join(os.path.dirname(__file__), "tpch_scalability_combined_subplots_no_zen5.png")
OUT_PATH = os.path.join(os.path.dirname(__file__), "tpch_scalability_combined_subplots_no_zen5.svg")
SCALE_FACTORS = ["sf1", "sf10", "sf30", "sf100", "sf300"]
#SCALE_FACTORS = ["sf1", "sf10", "sf30", "sf100"]

MACHINES = {
    "pi5":     {"label": "Raspberry Pi 5",  "color": "#e6194b", "marker": "o", "linestyle": "-"},
    "m1":      {"label": "Apple M1 Pro",        "color": "#f58231", "marker": "v", "linestyle": (0, (3, 1, 1, 1))},
    "m4":      {"label": "Apple M4 Max",    "color": "#3cb44b", "marker": "s", "linestyle": "--"},
    "p620":    {"label": "AMD EPYC (Zen 2)",     "color": "#911eb4", "marker": "D", "linestyle": "-."},
    #"zen5":    {"label": "AMD EPYC (Zen 5)", "color": "#4363d8", "marker": "^", "linestyle": ":"},
    "r6a-2xlarge": {"label": "r6a.2xlarge", "color": "#33c7d8", "marker": "X", "linestyle": (0, (5, 3))},
}

MAX_THREADS = {
    "zen5": 128,
    "p620": 64,
}

DARK_GREY = "#404040"
BI_LINES = [
    ("BI Low", 0.008, "x", ":"),
    ("BI High", 0.5, "*", (0, (3, 3))),
]


def cpuset_to_threads(cpuset: str) -> int:
    m = re.match(r"cpuset_(\d+)(?:-(\d+))?$", cpuset)
    if m.group(2) is None:
        return 1
    return int(m.group(2)) + 1


ALL_THREADS = set()
for machine in MACHINES:
    max_threads = MAX_THREADS.get(machine)
    for sf in SCALE_FACTORS:
        sf_dir = os.path.join(DATA_ROOT, machine, sf)
        if not os.path.isdir(sf_dir):
            continue
        for cpuset in os.listdir(sf_dir):
            if not os.path.isfile(os.path.join(sf_dir, cpuset, "tpch_summary.json")):
                continue
            threads = cpuset_to_threads(cpuset)
            if max_threads is not None and threads > max_threads:
                continue
            ALL_THREADS.add(threads)
ALL_THREADS = sorted(ALL_THREADS)
THREAD_TO_IDX = {t: i for i, t in enumerate(ALL_THREADS)}

fig, axes = plt.subplots(
    1, len(SCALE_FACTORS),
    figsize=(24, 3),
    gridspec_kw={"wspace": 0.15},
)

for ax, sf in zip(axes, SCALE_FACTORS):
    sf_num = sf.replace("sf", "")

    for machine, style in MACHINES.items():
        sf_dir = os.path.join(DATA_ROOT, machine, sf)
        if not os.path.isdir(sf_dir):
            continue
        max_threads = MAX_THREADS.get(machine)
        points = []
        for cpuset in sorted(os.listdir(sf_dir)):
            summary_path = os.path.join(sf_dir, cpuset, "tpch_summary.json")
            if not os.path.isfile(summary_path):
                continue
            threads = cpuset_to_threads(cpuset)
            if max_threads is not None and threads > max_threads:
                continue
            with open(summary_path) as f:
                data = json.load(f)[0]
            points.append((threads, data["queries_per_second"]))

        points.sort()
        threads, ys = zip(*points)
        xs = [THREAD_TO_IDX[t] for t in threads]
        ax.plot(xs, ys, label=style["label"], color=style["color"],
                marker=style["marker"], linestyle=style["linestyle"],
                markersize=7, linewidth=2)

    x_range = list(range(len(ALL_THREADS)))
    for name, val, marker, linestyle in BI_LINES:
        ax.plot(x_range, [val] * len(x_range), label=name, color=DARK_GREY,
                marker=marker, linestyle=linestyle, linewidth=1.5, markersize=7)

    ax.set_xticks(range(len(ALL_THREADS)))
    ax.set_xticklabels([str(t) for t in ALL_THREADS])
    ax.set_xlabel(rf"\# Threads (SF={sf_num})", fontsize=19)
    if ax is axes[0]:
        ax.set_ylabel("Throughput (Q/s)", fontsize=19)
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, which="major", linestyle="--", alpha=0.5)
    _, ymax = ax.get_ylim()
    ax.set_ylim(bottom=0, top=ymax * 1.08)
    ax.set_xlim(left=-0.5, right=len(ALL_THREADS) - 0.5)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles, labels,
    loc="lower center",
    bbox_to_anchor=(0.5, 0.9),
    ncol=len(handles),
    fontsize=19,
    borderaxespad=0,
    columnspacing=1.0,
    handletextpad=0.4,
    handlelength=1.5,
)

fig.tight_layout(pad=0.3, rect=[0, 0, 1, 1.0])
fig.savefig(OUT_PATH, bbox_inches="tight")
print(f"Saved to {OUT_PATH}")
