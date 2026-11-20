import argparse
import os
import matplotlib.pyplot as plt
from alternative import Alternative
from example import Example, set_vldb_style

# Reference CPU workload, independent of continuously billed cloud hours.
CLOUD_CORES = 4
UTILIZATIONS = [0.3, 0.6, 0.9]

# --- Output location for figures ---
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "plots")

# --- VLDB / two-column layout geometry (inches) ---
COLUMN_WIDTH = 3.33   # single column width
ROW_HEIGHT = 0.5      # height of a single subplot row

MACHINES = {
    "P5":      {"label": "Pi5",  "color": "#e6194b", "linestyle": "-", "linewidth": 1},
    "P5-NC":   {"label": "Pi5-NC",  "color": "#e6194b", "linestyle": ":", "linewidth": 1},
    "M1":      {"label": "M1",        "color": "#f58231", "linestyle": "-", "linewidth": 1},
    "M1-NC":   {"label": "M1-NC",     "color": "#f58231", "linestyle": ":", "linewidth": 1},
    "M4":      {"label": "M4",    "color": "#3cb44b", "linestyle": "-", "linewidth": 1},
    "M4-NC":   {"label": "M4-L-NC", "color": "#3cb44b", "linestyle": ":", "linewidth": 1},
    "M4-C":   {"label": "M4-C", "color": "#00670E", "linestyle": "-", "linewidth": 1},
    "Z2":    {"label": "Z2", "color": "#4363d8", "linestyle": "-", "linewidth": 1},
    "Z2-NC":    {"label": "Z2-NC", "color": "#4363d8", "linestyle": ":", "linewidth": 1},
    "R6a":    {"label": "R6a", "color": "#000000", "linestyle": "-", "linewidth": 1},
}

# Per-instance local machine specs (same values as make_all_examples.py).
LOCAL_SPECS = {
    "P5": dict(capex=355, tdp_watts=25, cores=4),     # Raspberry Pi 5
    "M1": dict(capex=3155, tdp_watts=60, cores=10),   # Apple M1 Pro
    "M4": dict(capex=5067.0, tdp_watts=80, cores=16), # Apple M4 Max (Mac Studio)
    "Z2": dict(capex=9580, tdp_watts=280, cores=64),  # AMD Zen 2
}


def _local_pair(name, cloud_utilization):
    """Returns (with CAPEX, without CAPEX) local alternatives for `name`."""
    spec = LOCAL_SPECS[name]
    common = dict(
        lifetime=6,
        tdp_watts=spec["tdp_watts"],
        baseline_utilization=0.1,
        cores=spec["cores"],
        cloud_cores=CLOUD_CORES,
        cloud_utilization=cloud_utilization,
        energy_price=0.34,    # $/kWh (Berlin)
        base_annual_opex=0.0,
    )
    return (Alternative.local(name=name, capex=spec["capex"], **common),
            Alternative.local(name=f"{name}-NC", capex=0, **common))


def build_examples(cloud_utilization):
    """Returns the row of examples (Pi5, M1, M4, Z2) for one cloud utilization."""
    r6a_2xlarge_cloud = Alternative.cloud(
        name="R6a",
        cores=CLOUD_CORES,
        lifetime=6,
        hourly_rate=0.66,  # $/hour https://aws.amazon.com/ec2/pricing/on-demand/
        discount_on_rate=0,
        hours_per_year=24*365,
        opex_growth=0.0,
        utilization=1.0,  # billed continuously
    )
    mac_cloud = Alternative.cloud(
        name="M4-C",
        lifetime=6,
        hourly_rate=1.476,  # $/hour https://aws.amazon.com/ec2/dedicated-hosts/pricing/
        discount_on_rate=0.75,  # 3-year commitment discount
        hours_per_year=24*365,
        opex_growth=0.0,
        utilization=1.0,  # billed continuously: EC2 Mac hosts have a 24h minimum
    )

    pi, pi_nc = _local_pair("P5", cloud_utilization)
    m1, m1_nc = _local_pair("M1", cloud_utilization)
    m4, m4_nc = _local_pair("M4", cloud_utilization)
    z2, z2_nc = _local_pair("Z2", cloud_utilization)
    return [
        Example(pi, r6a_2xlarge_cloud, pi_nc),
        Example(m1, r6a_2xlarge_cloud, m1_nc),
        Example(m4, r6a_2xlarge_cloud, m4_nc),
        Example(z2, r6a_2xlarge_cloud, z2_nc),
    ]


def plot_utilizations(utilizations, save_path, r=0.05):
    rows = [build_examples(u) for u in utilizations]
    ncols = len(rows[0])
    fig, axs = plt.subplots(
        len(utilizations), ncols,
        figsize=(COLUMN_WIDTH*2.1, ROW_HEIGHT*len(utilizations)),
        sharey=True, sharex=True, squeeze=False,
        gridspec_kw={"hspace": 0.3, "wspace": 0.05},
    )

    for i, (u, examples) in enumerate(zip(utilizations, rows)):
        for ax, example in zip(axs[i], examples):
            example.plot_break_even(r, time_units="day", ax=ax, machines=MACHINES)
            ax.set_ylim(top=7e6)
            ax.set_xlabel("")
            ylabel = ax.get_ylabel()
            ax.set_ylabel("")
            # Each column has the same alternatives; keep legends on the top row only.
            if i > 0:
                ax.get_legend().remove()
        axs[i][-1].text(1.02, 0.5, f"{u * 100:.0f}\%", transform=axs[i][-1].transAxes,
            ha="left", va="center", fontsize=8)

        axs[0][-1].text(1.1, 1.05, r"$u_{DB}$", transform=axs[0][-1].transAxes,
                ha="center", va="bottom", fontsize=8)

    fig.supylabel(ylabel, x=0.04, fontsize=10)
    # Offset in points below the bottom row so the label is independent of row count.
    axs[-1][0].annotate("Day", xy=(0.5, 0), xycoords=("figure fraction", "axes fraction"),
                        xytext=(0, -20), textcoords="offset points",
                        ha="center", va="top", fontsize=10)
    fig.savefig(save_path, bbox_inches="tight", pad_inches=0.1)
    print(f"Saved figure to {save_path}")
    return fig, axs


def main():
    parser = argparse.ArgumentParser(
        description="Break-even subplots with one row per cloud utilization.")
    parser.add_argument("utilizations", nargs="*", type=float, default=UTILIZATIONS,
                        help="cloud utilization fractions, e.g. 0.3 0.6 0.9")
    parser.add_argument("-o", "--output",
                        default=os.path.join(PLOTS_DIR, "break_even_utilizations.svg"))
    parser.add_argument("--no-tex", action="store_true",
                        help="render without a LaTeX installation")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    set_vldb_style(usetex=not args.no_tex)
    plot_utilizations(args.utilizations, args.output)


if __name__ == "__main__":
    main()
