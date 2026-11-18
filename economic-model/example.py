from alternative import Alternative
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt


# --- Output location for figures ---
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "plots")

# --- VLDB / two-column layout geometry (inches) ---
COLUMN_WIDTH = 3.33   # single column width
FIGURE_HEIGHT = 1.3     # single-column figure height
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
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 10,
        "figure.titlesize": 10,
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
    Compares two or more investment alternatives by their present worth of costs.
    """

    def __init__(self, alt_a, alt_b, alt_c=None):
        self.alt_a = alt_a # Always local with CAPEX
        self.alt_b = alt_b # Always cloud with OPEX
        self.alt_c = alt_c # Optional local alternative with no CAPEX (e.g. donated hardware or free cloud credits)

    @property
    def alternatives(self):
        alts = [self.alt_a, self.alt_b]
        if self.alt_c is not None:
            alts.append(self.alt_c)
        return alts

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
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2,
                  frameon=False, labelspacing=0.3)
        fig.tight_layout(pad=0.5)
        if save_path is not None:
            fig.savefig(save_path)
        plt.show()


    def plot_cumulative_cash_flows(self, r_values, save_paths=None,
                                   time_units="year"):
        """
        Plots cumulative (discounted) cash flows over the lifetime, producing
        one independent figure per alternative (one line per discount rate).

        r_values: iterable of discount rates, e.g. (0.02, 0.05, 0.10)
        save_paths: optional mapping {alternative_name: path} (e.g. .svg files)
            specifying where to write each figure.
        time_units: "year" (default) or "day"/"days". If "day", the x-axis is
            in days and costs are distributed uniformly per day.
        """
        save_paths = save_paths or {}
        for alt in self.alternatives:
            fig, ax = plt.subplots(figsize=(COLUMN_WIDTH, FIGURE_HEIGHT))
            for r in r_values:
                if time_units.lower() in ("day", "days"):
                    x_vals, cumulative = alt.cumulative_present_worth_daily(r)
                    unit_label = "Day"
                else:
                    x_vals, cumulative = alt.cumulative_present_worth(r)
                    unit_label = "Year"
                ax.plot(x_vals, [abs(c) for c in cumulative],
                        label=f"r={r*100:.0f}{_pct()}")

            ax.set_xlabel(unit_label)
            ax.set_ylabel("Cum. present worth (\$)" if matplotlib.rcParams.get("text.usetex") else "Cum. present worth ($)")
            ax.set_ylim(bottom=0)
            ax.set_title(alt.name)
            ax.grid(True, alpha=0.3)
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2,
                      frameon=False, labelspacing=0.3)
            fig.tight_layout(pad=0.5)

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

    def plot_break_even(self, r, save_path=None, time_units="year", scale="log", ax=None, machines=None):
        """
        For a single discount rate `r`, plot all alternatives' cumulative
        cost curves in one axes and annotate the break-even point.

        save_path: if given, the figure is written there (e.g. an .svg file).
        time_units: "year" (default) or "day"/"days". If "day", the x-axis is
            in days and costs are distributed uniformly per day.
        ax: optional matplotlib axis. If None, creates a new figure.
        machines: optional dict mapping alternative names to plot config dicts
                  with keys like "color", "marker", "linestyle".
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(COLUMN_WIDTH, FIGURE_HEIGHT))
            created_figure = True
        else:
            created_figure = False
            fig = ax.get_figure()

        if time_units.lower() in ("day", "days"):
            unit_label = "Day"
            unit_short = "days"
        else:
            unit_label = "Year"
            unit_short = "yr"

        # Get cumulative data for all alternatives
        alt_data = []
        for alt in self.alternatives:
            if time_units.lower() in ("day", "days"):
                x_vals, cum = alt.cumulative_present_worth_daily(r)
                # print first 10 days of cumulative cash flows for debugging
                # print(f"{alt.name} cumulative cash flows (first 10 days):")
                for day, c in zip(x_vals[:10], cum[:10]):
                    print(f"{alt.name} Day {day}: {c:.2f}")
            else:
                x_vals, cum = alt.cumulative_present_worth(r)
                print(f"{alt.name} cumulative cash flows (years):")
                for year, c in zip(x_vals, cum):
                    print(f"{alt.name} Year {year}: {c:.2f}")
            
            # Apply styling from machines dict if available
            plot_kwargs = {"label": alt.name}
            if machines and alt.name in machines:
                config = machines[alt.name]
                if "color" in config:
                    plot_kwargs["color"] = config["color"]
                if "marker" in config:
                    plot_kwargs["marker"] = config["marker"]
                if "linestyle" in config:
                    plot_kwargs["linestyle"] = config["linestyle"]
                if "linewidth" in config:
                    plot_kwargs["linewidth"] = config["linewidth"]
            
            ax.plot(x_vals, [abs(c) for c in cum], **plot_kwargs)
            alt_data.append((alt, x_vals, cum))

        # Find break-even point between alt_a and alt_b
        x_vals_a, cum_a = alt_data[0][1], alt_data[0][2]
        x_vals_b, cum_b = alt_data[1][1], alt_data[1][2]
        gap = [abs(b) - abs(a) for a, b in zip(cum_a, cum_b)]  # alt_b - alt_a
        be = None
        for i in range(1, len(gap)):
            if gap[i - 1] < 0 <= gap[i]:
                # Linear interpolation of the crossing
                frac = -gap[i - 1] / (gap[i] - gap[i - 1])
                tau = x_vals_a[i - 1] + frac
                cost = abs(cum_a[i - 1]) + frac * (abs(cum_a[i]) - abs(cum_a[i - 1]))
                be = (tau, cost)
                break

        if be is not None:
            tau, cost = be
            if time_units.lower() in ("day", "days"):
                offset = 500
            else:
                offset = 0.5
            ax.plot([tau], [cost], marker="*", markersize=5,
                    color="black", zorder=5, markeredgewidth=0)
            ax.axvline(tau, color="gray", linestyle="--", linewidth=0.8,
                       alpha=0.7)
            # Annotate break-even point with text positioned down and right
            ax.text(tau + offset, 4e6, f"CO:{tau:.0f} days", 
                    fontsize=7, ha="center", va="top")

        ax.set_xlabel(unit_label)
        ax.set_ylabel("C.PWC (\$)" if matplotlib.rcParams.get("text.usetex") else "Cum. present worth ($)")
        # ax.set_ylim(bottom=0)
        if scale == "log":
            ax.set_yscale("log")
            ax.set_ylim(bottom=1)  # log scale cannot show zero
            ax.set_yticks([1, 10000, 10000000])

        ax.set_xlim(left=-100, right=max(x_vals_a[-1], x_vals_b[-1])*1.05)
        ax.set_xticks([0, 500, 1000, 1500, 2000])
        # ax.set_title(f"\\textit{{r}}={r*100:.0f}{_pct()}")
        ax.grid(True, alpha=0.3)

        handles, labels = ax.get_legend_handles_labels()

        # desired order of labels
        if self.alt_c is not None:
            order = [self.alt_a.name, self.alt_c.name, self.alt_b.name]

        # reorder handles and labels together
        ordered = [(h, l) for h, l in zip(handles, labels) if l in order]
        ordered = sorted(ordered, key=lambda hl: order.index(hl[1]))
        handles_ordered, labels_ordered = zip(*ordered)

        ax.legend(handles_ordered, labels_ordered, loc="upper center", bbox_to_anchor=(0.5, 1.7), ncol=3,
                  frameon=True, columnspacing=0.4, handlelength=0.7, fontsize=7, handletextpad=0.1)
        # fig.tight_layout(pad=0.5)
        if save_path is not None:
            fig.savefig(save_path)

        return ax
        # plt.show()


# mac_local = Alternative.local(
#     name="M4 Local",
#     capex=5067.0,  # $ (Mac Studio M4) https://www.apple.com/de/shop/buy-mac/mac-studio/m4-max-chip-16-core-cpu-40%E2%80%91core-gpu-64-gb-arbeitsspeicher-1tb-speicher
#     lifetime=6,
#     tdp_watts=80,         # assumed average TDP for the chip/system
#     utilization=0.3,      # % utilization
#     energy_price=0.34,    # $/kWh (Berlin)
#     base_annual_opex=0.0  # ignored because TDP info is provided
# )

# mac_cloud = Alternative.cloud(
#     name="M4 Cloud",
#     lifetime=6,
#     # annual_opex=4050.0,
#     hourly_rate=1.476,  # $/hour https://aws.amazon.com/ec2/dedicated-hosts/pricing/
#     discount_on_rate=0.75,  # discount if commit to 3 years (https://aws.amazon.com/ec2/dedicated-hosts/pricing/)
#     hours_per_year=24*365,  # 8,760 hours/year
#     opex_growth=0.0,
#     utilization=1.0,  # billed continuously: EC2 Mac hosts have a 24h minimum
# )

# pi_local = Alternative.local(
#     name="Pi5",
#     capex=215,  # $ (Raspberry Pi 4 Model B) https://www.berrybase.de/en/raspberry-pi-5-8gb-ram?srsltid=AfmBOor86ohg-H6TTRC6Kv5W5LaccEJzPzlemO4yWzqEgdfHiyDbS2Ez
#     lifetime=6,
#     tdp_watts=25,         # assumed average TDP for the Raspberry Pi 5
#     utilization=0.3,     # % utilization
#     energy_price=0.34,   # $/kWh (Berlin)
#     base_annual_opex=0.0  # ignored because TDP info is provided
# )

# r6a_2xlarge_cloud = Alternative.cloud(
#     name="R6a.2xlarge",
#     lifetime=6,
#     hourly_rate=0.45,  # $/hour https://aws.amazon.com/ec2/pricing/on-demand/
#     discount_on_rate=0,  # discount if commit to 3 years (https://aws.amazon.com/ec2/dedicated-hosts/pricing/)
#     hours_per_year=24*365,  # 8,760 hours/year
#     opex_growth=0.0,
#     utilization=1.0,  # billed continuously
# )

# example_mac = Example(mac_local, mac_cloud)
# example_r6a = Example(pi_local, r6a_2xlarge_cloud)
# example_mac.print_present_worths()

# # Match the VLDB template (Libertine via LaTeX). Set usetex=False if LaTeX
# # is not installed on this machine.
# set_vldb_style(usetex=True)

# os.makedirs(PLOTS_DIR, exist_ok=True)

# # Example usage
# # r_vals = np.linspace(0.0, 0.15, 16)  # 0% to 15%
# # example_mac.plot_vs_r(
# #     r_vals, save_path=os.path.join(PLOTS_DIR, "pwc_vs_discount_rate.svg"))

# # example_r6a.plot_vs_r(
# #     r_vals, save_path=os.path.join(PLOTS_DIR, "pwc_vs_discount_rate_r6a.svg"))

# # # Cumulative discounted cash flows over the lifetime at a few discount rates
# # example_mac.plot_cumulative_cash_flows(
# #     [0.02, 0.05, 0.10],
# #     save_paths={
# #         mac_local.name: os.path.join(PLOTS_DIR, "cumulative_mac_local.svg"),
# #         mac_cloud.name: os.path.join(PLOTS_DIR, "cumulative_mac_cloud.svg"),
# #     })

# # example_r6a.plot_cumulative_cash_flows(
# #     [0.02, 0.05, 0.10],
# #     save_paths={
# #         r6a_2xlarge_cloud.name: os.path.join(PLOTS_DIR, "cumulative_r6a.svg"),
# #         pi_local.name: os.path.join(PLOTS_DIR, "cumulative_pi.svg"),
# #     })

# # # Both curves in one plot at a single rate, with the break-even point marked
# # example_mac.plot_break_even(
# #     0.05, save_path=os.path.join(PLOTS_DIR, "break_even_mac.svg"))

# example_mac.plot_break_even(
#     0.05, save_path=os.path.join(PLOTS_DIR, "break_even_mac.svg"), time_units="day")

# example_r6a.plot_break_even(
#     0.05, save_path=os.path.join(PLOTS_DIR, "break_even_r6a.svg"), time_units="day")
