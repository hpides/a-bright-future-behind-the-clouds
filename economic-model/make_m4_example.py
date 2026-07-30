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



mac_local = Alternative.local(
    name="M4 Local",
    capex=5067.0,  # $ (Mac Studio M4) https://www.apple.com/de/shop/buy-mac/mac-studio/m4-max-chip-16-core-cpu-40%E2%80%91core-gpu-64-gb-arbeitsspeicher-1tb-speicher
    lifetime=6,
    tdp_watts=80,         # assumed average TDP for the chip/system
    utilization=0.3,      # % utilization
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

example_mac = Example(mac_local, mac_cloud)
example_mac.print_present_worths()

# Match the VLDB template (Libertine via LaTeX). Set usetex=False if LaTeX
# is not installed on this machine.
set_vldb_style(usetex=True)

os.makedirs(PLOTS_DIR, exist_ok=True)

example_mac.plot_break_even(
    0.05, save_path=os.path.join(PLOTS_DIR, "break_even_mac.svg"), time_units="day")