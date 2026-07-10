from alternative import Alternative
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt


# --- Output location for figures ---
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "plots")

# --- VLDB / two-column layout geometry (inches) ---
COLUMN_WIDTH = 3.33   # single column width
FIGURE_HEIGHT = 2.0     # single-column figure height
TEXT_WIDTH = 7.0      # full text (both columns) width


def set_vldb_style(usetex=True):
    """
    Configure matplotlib to match the VLDB template: Linux Libertine serif
    fonts (via LaTeX) with font sizes large enough for a two-column layout.

    Set usetex=False to fall back to a Libertine-like serif without invoking
    a LaTeX installation (labels still render correctly).
    """
    rc = {
        "font.family": "serif",
        "font.serif": ["Linux Libertine O", "Linux Libertine",
                       "Libertinus Serif", "DejaVu Serif"],
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 13,
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.8,
        "lines.markersize": 4,
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


def _pct():
    """Percent sign that is safe under both usetex and mathtext."""
    return r"\%" if matplotlib.rcParams.get("text.usetex") else "%"


class Example:
    """
    Compares two investment alternatives by their present worth of costs.
    """

    def __init__(self, alt_a, alt_b):
        self.alt_a = alt_a
        self.alt_b = alt_b

    @property
    def alternatives(self):
        return [self.alt_a, self.alt_b]

    def print_present_worths(self, r_values=(0.02, 0.05, 0.10)):
        for r in r_values:
            pw_a = self.alt_a.present_worth_cost(r)
            pw_b = self.alt_b.present_worth_cost(r)
            print(f"r={r*100:.0f}%: {self.alt_a.name}={pw_a:,.0f} €, "
                  f"{self.alt_b.name}={pw_b:,.0f} €")

    def plot_vs_r(self, r_values, save_path=None):
        """
        r_values: iterable of discount rates, e.g. np.linspace(0.0, 0.15, 16)
        save_path: if given, the figure is written there (e.g. an .svg file).
        """
        fig, ax = plt.subplots(figsize=(COLUMN_WIDTH, FIGURE_HEIGHT))
        for alt in self.alternatives:
            pw_costs = [abs(alt.present_worth_cost(r)) for r in r_values]
            ax.plot([r * 100 for r in r_values], pw_costs, label=alt.name)

        ax.set_xlabel(f"Discount rate ({_pct()})")
        ax.set_ylabel("Present worth of cost (USD)")
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), ncol=1,
                  frameon=False)
        fig.tight_layout()
        if save_path is not None:
            fig.savefig(save_path)
        plt.show()


    def plot_cumulative_cash_flows(self, r_values, save_paths=None):
        """
        Plots cumulative (discounted) cash flows over the lifetime, producing
        one independent figure per alternative (one line per discount rate).

        r_values: iterable of discount rates, e.g. (0.02, 0.05, 0.10)
        save_paths: optional mapping {alternative_name: path} (e.g. .svg files)
            specifying where to write each figure.
        """
        save_paths = save_paths or {}
        for alt in self.alternatives:
            fig, ax = plt.subplots(figsize=(COLUMN_WIDTH, FIGURE_HEIGHT))
            for r in r_values:
                years, cumulative = alt.cumulative_present_worth(r)
                ax.plot(years, [abs(c) for c in cumulative], marker="o",
                        label=f"r={r*100:.0f}{_pct()}")

            ax.set_xlabel("Year")
            ax.set_ylabel("Cum. present worth (\$)" if matplotlib.rcParams.get("text.usetex") else "Cum. present worth ($)")
            ax.set_ylim(bottom=0)
            ax.set_title(alt.name)
            ax.grid(True, alpha=0.3)
            ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), ncol=1,
                      frameon=False)
            fig.tight_layout()

            path = save_paths.get(alt.name)
            if path is not None:
                fig.savefig(path)
            plt.show()


    def break_even(self, r):
        """
        Break-even point at discount rate `r`: the time at which the cumulative
        cost of alt_b (cloud) surpasses that of alt_a (local).

        Returns (tau, cost) with a linearly interpolated (fractional-year) tau,
        or None if no crossing occurs within the lifetime.
        """
        years_a, cum_a = self.alt_a.cumulative_present_worth(r)
        years_b, cum_b = self.alt_b.cumulative_present_worth(r)

        # Work with positive cost magnitudes.
        gap = [abs(b) - abs(a) for a, b in zip(cum_a, cum_b)]  # cloud - local

        for i in range(1, len(gap)):
            if gap[i - 1] < 0 <= gap[i]:
                # Linear interpolation of the crossing between year i-1 and i.
                frac = -gap[i - 1] / (gap[i] - gap[i - 1])
                tau = years_a[i - 1] + frac
                cost = abs(cum_a[i - 1]) + frac * (abs(cum_a[i]) - abs(cum_a[i - 1]))
                return tau, cost
        return None

    def plot_break_even(self, r, save_path=None):
        """
        For a single discount rate `r`, plot both alternatives' cumulative
        cost curves in one axes and annotate the break-even point.

        save_path: if given, the figure is written there (e.g. an .svg file).
        """
        fig, ax = plt.subplots(figsize=(COLUMN_WIDTH, FIGURE_HEIGHT))

        for alt in self.alternatives:
            years, cumulative = alt.cumulative_present_worth(r)
            ax.plot(years, [abs(c) for c in cumulative],
                    marker="o", label=alt.name)

        be = self.break_even(r)
        if be is not None:
            tau, cost = be
            ax.plot([tau], [cost], marker="*", markersize=12,
                    color="black", zorder=5)
            ax.axvline(tau, color="gray", linestyle="--", linewidth=0.8,
                       alpha=0.7)
            ax.annotate(f"Break-even\n{tau:.1f} yr",
                        xy=(tau, cost),
                        xytext=(tau, cost + 0.12 * (ax.get_ylim()[1] - cost)),
                        ha="center", va="bottom",
                        arrowprops=dict(arrowstyle="->", color="black",
                                        lw=0.8))

        ax.set_xlabel("Year")
        ax.set_ylabel("Cum. present worth (\$)" if matplotlib.rcParams.get("text.usetex") else "Cum. present worth ($)")
        ax.set_ylim(bottom=0)
        ax.set_title(f"Cumulative cost at r={r*100:.0f}{_pct()}")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), ncol=1,
                  frameon=False)
        fig.tight_layout()
        if save_path is not None:
            fig.savefig(save_path)
        plt.show()


mac_local = Alternative.local(
    name="M4 Local",
    capex=5067.0,  # $ (Mac Studio M4) https://www.apple.com/de/shop/buy-mac/mac-studio/m4-max-chip-16-core-cpu-40%E2%80%91core-gpu-64-gb-arbeitsspeicher-1tb-speicher
    lifetime=6,
    tdp_watts=80,         # assumed average TDP for the chip/system
    utilization=0.5,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

mac_cloud = Alternative.cloud(
    name="M4 Cloud",
    lifetime=6,
    # annual_opex=4050.0,
    hourly_rate=1.476,  # $/hour https://aws.amazon.com/ec2/dedicated-hosts/pricing/
    discount_on_rate=0.75,  # discount if commit to 3 years (https://aws.amazon.com/ec2/dedicated-hosts/pricing/)
    hours_per_year=24*365,  # 8,760 hours/year
    opex_growth=0.0,
    utilization=1.0,  # billed continuously: EC2 Mac hosts have a 24h minimum
)

example = Example(mac_local, mac_cloud)
example.print_present_worths()

# Match the VLDB template (Libertine via LaTeX). Set usetex=False if LaTeX
# is not installed on this machine.
set_vldb_style(usetex=True)

os.makedirs(PLOTS_DIR, exist_ok=True)

# Example usage
r_vals = np.linspace(0.0, 0.15, 16)  # 0% to 15%
example.plot_vs_r(
    r_vals, save_path=os.path.join(PLOTS_DIR, "pwc_vs_discount_rate.svg"))

# Cumulative discounted cash flows over the lifetime at a few discount rates
example.plot_cumulative_cash_flows(
    [0.02, 0.05, 0.10],
    save_paths={
        mac_local.name: os.path.join(PLOTS_DIR, "cumulative_local.svg"),
        mac_cloud.name: os.path.join(PLOTS_DIR, "cumulative_cloud.svg"),
    })

# Both curves in one plot at a single rate, with the break-even point marked
example.plot_break_even(
    0.05, save_path=os.path.join(PLOTS_DIR, "break_even.svg"))
