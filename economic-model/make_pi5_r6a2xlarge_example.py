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
FIGURE_HEIGHT = 1.3     # single-column figure height
TEXT_WIDTH = 7.0      # full text (both columns) width


pi_local = Alternative.local(
    name="Pi5",
    capex=355,  # $ (Raspberry Pi 5 Model B) https://www.berrybase.de/en/raspberry-pi-5-16gb-ram
    lifetime=6,
    tdp_watts=25,         # assumed average TDP for the Raspberry Pi 5
    utilization=0.3,     # % utilization
    energy_price=0.34,   # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)

pi_local_no_capex = Alternative.local(
    name="Pi5-NoCAPEX",
    capex=0,  # $ (Raspberry Pi 5 Model B) https://www.berrybase.de/en/raspberry-pi-5-16gb-ram
    lifetime=6,
    tdp_watts=25,         # assumed average TDP for the Raspberry Pi 5
    utilization=0.3,     # % utilization
    energy_price=0.34,   # $/kWh (Berlin)
    base_annual_opex=0.0  # ignored because TDP info is provided
)


r6a_2xlarge_cloud = Alternative.cloud(
    name="R6a.2xlarge",
    lifetime=6,
    hourly_rate=0.45,  # $/hour https://aws.amazon.com/ec2/pricing/on-demand/
    discount_on_rate=0,  # discount if commit to 3 years (https://aws.amazon.com/ec2/dedicated-hosts/pricing/)
    hours_per_year=24*365,  # 8,760 hours/year
    opex_growth=0.0,
    utilization=1.0,  # billed continuously
)

example_r6a = Example(pi_local, r6a_2xlarge_cloud, pi_local_no_capex)

# Match the VLDB template (Libertine via LaTeX). Set usetex=False if LaTeX
# is not installed on this machine.
set_vldb_style(usetex=True)

os.makedirs(PLOTS_DIR, exist_ok=True)

example_r6a.plot_break_even(
    0.05, save_path=os.path.join(PLOTS_DIR, "break_even_r6a.svg"), time_units="day")