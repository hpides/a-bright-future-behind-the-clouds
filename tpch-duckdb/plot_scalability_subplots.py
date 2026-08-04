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
# OUT_PATH = os.path.join(os.path.dirname(__file__), "tpch_scalability_combined_subplots.png")
OUT_PATH = os.path.join(os.path.dirname(__file__), "tpch_scalability_combined_subplots.svg")
SCALE_FACTORS = ["sf10", "sf30", "sf100"]

MACHINES = {
    "pi5":     {"label": "Raspberry Pi 5",  "color": "#e6194b", "marker": "o", "linestyle": "-"},
    "m1":      {"label": "Apple M1",        "color": "#f58231", "marker": "v", "linestyle": (0, (3, 1, 1, 1))},
    "m4":      {"label": "Apple M4 Max",    "color": "#3cb44b", "marker": "s", "linestyle": "--"},
    "zen5":    {"label": "AMD EPYC (Zen 5)", "color": "#4363d8", "marker": "^", "linestyle": ":"},
    "p620":    {"label": "Lenovo P620",     "color": "#911eb4", "marker": "D", "linestyle": "-."},
}

def cpuset_to_threads(cpuset: str) -> int:
    m = re.match(r"cpuset_(\d+)(?:-(\d+))?$", cpuset)
    if m.group(2) is None:
        return 1
    return int(m.group(2)) + 1


ALL_THREADS = set()
for machine in MACHINES:
    for sf in SCALE_FACTORS:
        sf_dir = os.path.join(DATA_ROOT, machine, sf)
        if not os.path.isdir(sf_dir):
            continue
        for cpuset in os.listdir(sf_dir):
            if not os.path.isfile(os.path.join(sf_dir, cpuset, "tpch_summary.json")):
                continue
            ALL_THREADS.add(cpuset_to_threads(cpuset))
ALL_THREADS = sorted(ALL_THREADS)
THREAD_TO_IDX = {t: i for i, t in enumerate(ALL_THREADS)}

fig, axes = plt.subplots(1, 3, figsize=(12, 3))

for ax, sf in zip(axes, SCALE_FACTORS):
    sf_num = sf.replace("sf", "")

    for machine, style in MACHINES.items():
        sf_dir = os.path.join(DATA_ROOT, machine, sf)
        if not os.path.isdir(sf_dir):
            continue
        points = []
        for cpuset in sorted(os.listdir(sf_dir)):
            summary_path = os.path.join(sf_dir, cpuset, "tpch_summary.json")
            if not os.path.isfile(summary_path):
                continue
            with open(summary_path) as f:
                data = json.load(f)[0]
            points.append((cpuset_to_threads(cpuset), data["queries_per_second"]))

        points.sort()
        threads, ys = zip(*points)
        xs = [THREAD_TO_IDX[t] for t in threads]
        ax.plot(xs, ys, label=style["label"], color=style["color"],
                marker=style["marker"], linestyle=style["linestyle"],
                markersize=7, linewidth=2)

    ax.set_xticks(range(len(ALL_THREADS)))
    ax.set_xticklabels([str(t) for t in ALL_THREADS])
    ax.set_xlabel(rf"\# Threads (SF={sf_num})", fontsize=19)
    if ax is axes[0]:
        ax.set_ylabel("Throughput (Q/s)", fontsize=19)
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, which="major", linestyle="--", alpha=0.5)
    _, ymax = ax.get_ylim()
    ax.set_ylim(bottom=0, top=ymax * 1.05)
    ax.set_xlim(left=-0.5, right=len(ALL_THREADS) - 0.5)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles, labels,
    loc="lower center",
    bbox_to_anchor=(0.5, 1.0),
    ncol=len(MACHINES),
    fontsize=19,
    borderaxespad=0,
    columnspacing=1.0,
    handletextpad=0.4,
    handlelength=1.5,
)

fig.tight_layout(pad=0.3, rect=[0, 0, 1, 1.0])
fig.savefig(OUT_PATH, bbox_inches="tight")
print(f"Saved to {OUT_PATH}")
