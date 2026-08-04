import json
import os
import re
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

usetex = True
rc = {
    "font.family": "serif",
    "font.serif": ["Linux Libertine O", "Linux Libertine",
                   "Libertinus Serif", "DejaVu Serif"],
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
}
if usetex:
    rc.update({
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage[T1]{fontenc}"
                               r"\usepackage[libertine]{libertine}",
    })
matplotlib.rcParams.update(rc)

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_DIR = os.path.join(os.path.dirname(__file__), "old_vs_new_threads")
SCALE_FACTORS = ["sf1", "sf10", "sf30", "sf100"]

# Only the generic machine name and its "-old-threads" counterpart are
# considered. Any other variant folder (e.g. *-threads-fixed-SR, *-base)
# is intentionally ignored.
MACHINES = {
    "pi5":  {"label": "Raspberry Pi 5",  "color": "#e6194b"},
    "m1":   {"label": "Apple M1",        "color": "#f58231"},
    "m4":   {"label": "Apple M4 Max",    "color": "#3cb44b"},
    "zen5": {"label": "AMD EPYC (Zen 5)", "color": "#4363d8"},
    "p620": {"label": "Lenovo P620",     "color": "#911eb4"},
}

VARIANTS = {
    "new": {"suffix": "", "style_label": "current threading", "marker": "o", "linestyle": "-"},
    "old": {"suffix": "-old-threads", "style_label": "old threading", "marker": "s", "linestyle": "--"},
}


def cpuset_to_threads(cpuset: str) -> int:
    """cpuset_0 -> 1, cpuset_0-N -> N+1."""
    m = re.match(r"cpuset_(\d+)(?:-(\d+))?$", cpuset)
    if m.group(2) is None:
        return 1
    return int(m.group(2)) + 1


def load_points(machine_dir, sf):
    sf_dir = os.path.join(machine_dir, sf)
    if not os.path.isdir(sf_dir):
        return []
    points = []
    for cpuset in sorted(os.listdir(sf_dir)):
        summary_path = os.path.join(sf_dir, cpuset, "tpch_summary.json")
        if not os.path.isfile(summary_path):
            continue
        with open(summary_path) as f:
            data = json.load(f)[0]
        points.append((cpuset_to_threads(cpuset), data["queries_per_second"]))
    points.sort()
    return points


os.makedirs(OUT_DIR, exist_ok=True)

for machine, machine_style in MACHINES.items():
    for sf in SCALE_FACTORS:
        sf_num = sf.replace("sf", "")

        series = {}
        for variant, vstyle in VARIANTS.items():
            machine_dir = os.path.join(DATA_ROOT, machine + vstyle["suffix"])
            points = load_points(machine_dir, sf)
            if points:
                series[variant] = points

        if not series:
            continue

        fig, ax = plt.subplots(figsize=(6, 4))

        for variant, points in series.items():
            vstyle = VARIANTS[variant]
            xs, ys = zip(*points)
            ax.plot(
                xs, ys,
                label=vstyle["style_label"],
                color=machine_style["color"],
                marker=vstyle["marker"],
                linestyle=vstyle["linestyle"],
                markersize=7,
                linewidth=2,
            )
            for x, y in zip(xs, ys):
                ax.annotate(
                    f"{y:.1f}",
                    (x, y),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    fontsize=10,
                    color=machine_style["color"],
                )

        all_threads = sorted({t for points in series.values() for t, _ in points})

        ax.set_xscale("log", base=2)
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v)}"))
        ax.xaxis.set_minor_formatter(ticker.NullFormatter())
        ax.set_xticks(all_threads)
        if len(all_threads) > 6:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        ax.set_xlabel("Number of Threads", fontsize=15)
        ax.set_ylabel("Queries per Second", fontsize=15)
        ax.set_title(f"{machine_style['label']} (SF={sf_num})", fontsize=15)
        ax.legend(fontsize=12, labelspacing=0.3, handletextpad=0.4, handlelength=1.5)
        ax.tick_params(axis="both", labelsize=13)
        ax.grid(True, which="major", linestyle="--", alpha=0.5)
        ax.grid(True, which="minor", linestyle=":", alpha=0.3)
        _, ymax = ax.get_ylim()
        ax.set_ylim(bottom=0, top=ymax * 1.15)
        ax.set_xlim(left=all_threads[0] * 0.75, right=all_threads[-1] * 1.4)

        fig.tight_layout()
        out_path = os.path.join(OUT_DIR, f"tpch_scalability_{machine}_old_vs_new_{sf}.svg")
        fig.savefig(out_path)
        plt.close(fig)
        print(f"Saved to {out_path}")
