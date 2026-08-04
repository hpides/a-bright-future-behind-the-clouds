import pandas as pd
import matplotlib.pyplot as plt

CSV_PATH = "Voltcraft SEM5000 DUAL_(202608)_power.csv"
OUT_PATH = "power_consumption.png"

# Palette (dataviz skill reference palette, light mode)
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES_1 = "#2a78d6"

with open(CSV_PATH) as f:
    lines = f.readlines()[9:]  # skip metadata/header block

power = pd.Series(
    [float(line.split(",")[3]) for line in lines if line.strip()]
)

# Smooth out sharp spikes with a centered rolling average
SMOOTH_WINDOW = 2
power_smooth = power.rolling(window=SMOOTH_WINDOW, center=True, min_periods=1).mean()

# Time is abstract: use elapsed minutes since the first sample (one reading/minute)
elapsed_min = power.index.to_numpy()

fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

ax.plot(elapsed_min, power_smooth, color=SERIES_1, linewidth=2, solid_capstyle="round")

ax.set_title("Power Consumption Over Time", color=INK_PRIMARY, fontsize=14, pad=14, loc="left")
ax.set_xlabel("Elapsed time (min)", color=INK_SECONDARY, fontsize=10)
ax.set_ylabel("Power (W)", color=INK_SECONDARY, fontsize=10)

ax.grid(True, axis="y", color=GRIDLINE, linewidth=1)
ax.set_axisbelow(True)

for spine_name, spine in ax.spines.items():
    if spine_name == "bottom":
        spine.set_color(BASELINE)
    else:
        spine.set_visible(False)

ax.tick_params(axis="both", colors=INK_MUTED, labelsize=9, length=0)

fig.tight_layout()
fig.savefig(OUT_PATH, facecolor=SURFACE)
print(f"Saved plot to {OUT_PATH}")
