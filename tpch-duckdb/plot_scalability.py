import json
import os
import re
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
SCALE_FACTORS = ["sf10", "sf30", "sf100"]
#SCALE_FACTORS = ["sf1", "sf10", "sf30"]

MACHINES = {
    "pi5":     {"label": "Raspberry Pi 5",  "color": "#e6194b", "marker": "o", "linestyle": "-"},
    "m4-max":  {"label": "Apple M4 Max",    "color": "#3cb44b", "marker": "s", "linestyle": "--"},
    "m4-base": {"label": "Apple M4",        "color": "#f58231", "marker": "v", "linestyle": (0, (3, 1, 1, 1))},
    "zen5":    {"label": "AMD EPYC (Zen 5)", "color": "#4363d8", "marker": "^", "linestyle": ":"},
    "p620":    {"label": "Lenovo P620",     "color": "#911eb4", "marker": "D", "linestyle": "-."},
}

def cpuset_to_threads(cpuset: str) -> int:
    """cpuset_0 → 1, cpuset_0-N → N+1."""
    m = re.match(r"cpuset_(\d+)(?:-(\d+))?$", cpuset)
    if m.group(2) is None:
        return 1
    return int(m.group(2)) + 1


for sf in SCALE_FACTORS:
    fig, ax = plt.subplots(figsize=(9, 5.5))
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
            threads = cpuset_to_threads(cpuset)
            qps = data["queries_per_second"]
            points.append((threads, qps))

        points.sort()
        xs, ys = zip(*points)
        ax.plot(
            xs, ys,
            label=style["label"],
            color=style["color"],
            marker=style["marker"],
            linestyle=style["linestyle"],
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
                fontsize=11,
                color=style["color"],
            )

    ax.set_xscale("log", base=2)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.set_xticks([1, 2, 4, 8, 16, 32, 64, 128, 192])

    ax.set_xlabel("Number of Threads", fontsize=15)
    ax.set_ylabel("Queries per Second", fontsize=15)
    ax.set_title(f"DuckDB TPC-H SF{sf_num} Scalability: Pi5 vs M4 vs Zen5 vs P620", fontsize=16, fontweight="bold")
    ax.legend(fontsize=14)
    ax.tick_params(axis="both", labelsize=14)
    ax.grid(True, which="major", linestyle="--", alpha=0.5)
    ax.grid(True, which="minor", linestyle=":", alpha=0.3)
    _, ymax = ax.get_ylim()
    ax.set_ylim(bottom=0, top=ymax * 1.15)
    ax.set_xlim(left=0.75, right=280)

    fig.tight_layout()
    out_path = os.path.join(os.path.dirname(__file__), f"tpch_scalability_combined_{sf}.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved to {out_path}")
