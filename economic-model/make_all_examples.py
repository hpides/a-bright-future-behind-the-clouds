from alternative import Alternative
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from example import Example, set_vldb_style

# --- Output location for figures ---
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "plots")

# --- VLDB / two-column layout geometry (inches) ---
COLUMN_WIDTH = 3.33   # single column width
FIGURE_HEIGHT = 0.5   # single-column figure height
TEXT_WIDTH = 7.0      # full text (both columns) width
os.makedirs(PLOTS_DIR, exist_ok=True)
# Match the VLDB template (Libertine via LaTeX). Set usetex=False if LaTeX
# is not installed on this machine.
set_vldb_style(usetex=True)

########################### Color Formatting for Plots ##########################################

# MACHINES = {
#     "P5":      {"label": "Pi5",  "color": "#e6194b", "marker": "o", "linestyle": "-"},
#     "P5-NC":   {"label": "Pi5-NC",  "color": "#e7436c", "marker": "o", "linestyle": "-"},
#     "M1":      {"label": "M1",        "color": "#f58231", "marker": "v", "linestyle": (0, (3, 1, 1, 1))},
#     "M1-NC":   {"label": "M1-NC",     "color": "#f7944e", "marker": "v", "linestyle": (0, (3, 1, 1, 1))},
#     "M4-L":      {"label": "M4",    "color": "#3cb44b", "marker": "s", "linestyle": "--"},
#     "M4-L-NC":   {"label": "M4-L-NC", "color": "#5cb568", "marker": "s", "linestyle": "--"},
#     "M4-C":   {"label": "M4-C", "color": "#048014", "marker": "s", "linestyle": "--"},
#     "Z5":    {"label": "Z5", "color": "#4363d8", "marker": "^", "linestyle": ":"},
#     "Z5-NC":    {"label": "Z5-NC", "color": "#5c77d8", "marker": "^", "linestyle": ":"},
#     # "p620":    {"label": "Lenovo P620",     "color": "#911eb4", "marker": "D", "linestyle": "-."},
# }

MACHINES = {
    "P5":      {"label": "Pi5",  "color": "#e6194b", "linestyle": "-", "linewidth": 1},
    "P5-NC":   {"label": "Pi5-NC",  "color": "#e6194b", "linestyle": ":", "linewidth": 1},
    "M1":      {"label": "M1",        "color": "#f58231", "linestyle": "-", "linewidth": 1},
    "M1-NC":   {"label": "M1-NC",     "color": "#f58231", "linestyle": ":", "linewidth": 1},
    "M4":      {"label": "M4",    "color": "#3cb44b", "linestyle": "-", "linewidth": 1},
    "M4-NC":   {"label": "M4-L-NC", "color": "#3cb44b", "linestyle": ":", "linewidth": 1},
    "M4-C":   {"label": "M4-C", "color": "#00670E", "linestyle": "-", "linewidth": 1},
    "Z5":    {"label": "Z5", "color": "#4363d8", "linestyle": "-", "linewidth": 1},
    "Z5-NC":    {"label": "Z5-NC", "color": "#4363d8", "linestyle": ":", "linewidth": 1},
    "R6a":    {"label": "R6a", "color": "#000000", "linestyle": "-", "linewidth": 1},
    # "p620":    {"label": "Lenovo P620",     "color": "#911eb4", "marker": "D", "linestyle": "-."},
}

#################################################################################################

############################ Mac 4 max Example ############################
##################################################################################################
##################################################################################################

mac_local = Alternative.local(
    name="M4",
    capex=5067.0,  # $ (Mac Studio M4) https://www.apple.com/de/shop/buy-mac/mac-studio/m4-max-chip-16-core-cpu-40%E2%80%91core-gpu-64-gb-arbeitsspeicher-1tb-speicher
    lifetime=6,
    tdp_watts=80,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

mac_local_no_capex = Alternative.local(
    name="M4-NC",
    capex=0,  # $ (Mac Studio M4) https://www.apple.com/de/shop/buy-mac/mac-studio/m4-max-chip-16-core-cpu-40%E2%80%91core-gpu-64-gb-arbeitsspeicher-1tb-speicher
    lifetime=6,
    tdp_watts=80,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

mac_cloud = Alternative.cloud(
    name="M4-C",
    lifetime=6,
    # annual_opex=4050.0,
    hourly_rate=1.476,  # $/hour https://aws.amazon.com/ec2/dedicated-hosts/pricing/
    discount_on_rate=0.75,  # discount if commit to 3 years (https://aws.amazon.com/ec2/dedicated-hosts/pricing/)
    hours_per_year=24*365,  # 8,760 hours/year
    opex_growth=0.0,
    utilization=1.0,  # billed continuously: EC2 Mac hosts have a 24h minimum
)

example_m4 = Example(mac_local, mac_cloud, mac_local_no_capex)
# ax_m4 = example_m4.plot_break_even(
#     0.05, save_path=os.path.join(PLOTS_DIR, "break_even_m4.svg"), time_units="day")

############################ Raspberry Pi 5 + AWS R6a.2xlarge example ############################
##################################################################################################
##################################################################################################

pi_local = Alternative.local(
    name="P5",
    capex=355,  # $ (Raspberry Pi 5 Model B) https://www.berrybase.de/en/raspberry-pi-5-16gb-ram
    lifetime=6,
    tdp_watts=25,         # assumed average TDP for the Raspberry Pi 5
    utilization=0.3,     # % utilization
    energy_price=0.34,   # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

pi_local_no_capex = Alternative.local(
    name="P5-NC",
    capex=0,  # $ (Raspberry Pi 5 Model B) https://www.berrybase.de/en/raspberry-pi-5-16gb-ram
    lifetime=6,
    tdp_watts=25,         # assumed average TDP for the Raspberry Pi 5
    utilization=0.3,     # % utilization
    energy_price=0.34,   # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)


r6a_2xlarge_cloud = Alternative.cloud(
    name="R6a",
    lifetime=6,
    hourly_rate=0.45,  # $/hour https://aws.amazon.com/ec2/pricing/on-demand/
    discount_on_rate=0,  # discount if commit to 3 years (https://aws.amazon.com/ec2/dedicated-hosts/pricing/)
    hours_per_year=24*365,  # 8,760 hours/year
    opex_growth=0.0,
    utilization=1.0,  # billed continuously
)

example_pi5_r6a = Example(pi_local, r6a_2xlarge_cloud, pi_local_no_capex)
# ax_pi5_r6a = example_pi5_r6a.plot_break_even(
#     0.05, save_path=os.path.join(PLOTS_DIR, "break_even_pi5_r6a.svg"), time_units="day")

############################ M1 local -  R6a.2xlarge #############################################
##################################################################################################
##################################################################################################

m1_local = Alternative.local(
    name="M1",
    capex=3155,  # $ (Mac Mini M1) https://www.apple.com/de/shop/buy-mac/mac-mini
    lifetime=6,
    tdp_watts=60,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

m1_local_no_capex = Alternative.local(
    name="M1-NC",
    capex=0,  # $ (Mac Mini M1) https://www.apple.com/de/shop/buy-mac/mac-mini
    lifetime=6,
    tdp_watts=60,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

example_m1 = Example(m1_local, r6a_2xlarge_cloud, m1_local_no_capex)
# ax_m1 = example_m1.plot_break_even(
#     0.05, save_path=os.path.join(PLOTS_DIR, "break_even_m1.svg"), time_units="day")

############################ Zen 2 local -  R6a.2xlarge #############################################
##################################################################################################
##################################################################################################

zen2_local = Alternative.local(
    name="Z2",
    capex=17688,  # $ (AMD Ryzen 7 3700X) https://www.amazon.com/AMD-Ryzen-3700X-16-Thread-Processor/dp/B07SXMZLP9
    lifetime=6,
    tdp_watts=280,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

zen2_local_no_capex = Alternative.local(
    name="Z2-NC",
    capex=0,  # $ (AMD Ryzen 7 3700X) https://www.amazon.com/AMD-Ryzen-3700X-16-Thread-Processor/dp/B07SXMZLP9
    lifetime=6,
    tdp_watts=280,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

example_zen2 = Example(zen2_local, r6a_2xlarge_cloud, zen2_local_no_capex)
# ax_zen2 = example_zen2.plot_break_even(
#     0.05, save_path=os.path.join(PLOTS_DIR, "break_even_zen2.svg"), time_units="day")

############################ Zen 5 local -  R6a.2xlarge #############################################
##################################################################################################
##################################################################################################


zen5_local = Alternative.local(
    name="Z5",
    capex=78135,  # $ (AMD Ryzen 9 7950X) https://www.amazon.com/AMD-Ryzen-9-7950X-Processor/dp/B0BBJQF7ZK
    lifetime=6,
    tdp_watts=550,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

zen5_local_no_capex = Alternative.local(
    name="Z5-NC",
    capex=0,  # $ (AMD Ryzen 9 7950X) https://www.amazon.com/AMD-Ryzen-9-7950X-Processor/dp/B0BBJQF7ZK
    lifetime=6,
    tdp_watts=550,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
    energy_price=0.34,    # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)
example_zen5 = Example(zen5_local, r6a_2xlarge_cloud, zen5_local_no_capex)
# ax_zen5 = example_zen5.plot_break_even(
#     0.05, save_path=os.path.join(PLOTS_DIR, "break_even_zen5.svg"), time_units="day")


####### Make 1 row subplots for all examples
fig, axs = plt.subplots(1, 4, figsize=(COLUMN_WIDTH*2.1, FIGURE_HEIGHT), sharey=True, sharex=True)

# Plot each example into its corresponding axis
for ax, example in zip(axs, [example_pi5_r6a, example_m1, example_m4, example_zen5]):
    example.plot_break_even(0.05, time_units="day", ax=ax, machines=MACHINES)

# Remove y-axis labels from all but the first subplot
for ax in axs[1:]:
    ax.set_ylabel("")

# Remove x-axis labels from all subplots
for ax in axs:
    ax.set_xlabel("")

# Add a single centered x-axis label below all subplots
fig.text(0.5, -0.5, "Day", ha="center", fontsize=10)

# fig.subplots_adjust(hspace=10)
# fig.tight_layout()
save_path=os.path.join(PLOTS_DIR, "break_even_all.svg")
plt.savefig(save_path, bbox_inches='tight', pad_inches=0.1)
# plt.show()

