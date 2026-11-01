#!/usr/bin/env python3
"""Charts for the A/B test peeking case study (Truth with Data, Nov 2026).
Usage: python3 charts.py OUT_DIR CHART_DIR
Reads the CSVs written by sequential_simulation.py. Site house style."""
import logging
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
OUT, CH = sys.argv[1], sys.argv[2]
os.makedirs(CH, exist_ok=True)
INK, MUTED, GRID, BLUE, AMBER, GREY, RED = "#0f172a", "#64748b", "#e2e8f0", "#2563eb", "#d97706", "#94a3b8", "#dc2626"
plt.rcParams.update({
    "font.family": ["Inter", "Segoe UI", "Arial", "sans-serif"], "svg.fonttype": "none",
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "axes.labelsize": 11,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "svg.hashsalt": "truthwithdata",
})
SRC = "Simulation: 50,000 tests per plan, 1,000 visitors per arm per day for 20 days, 5% conversion. Analysis: truthwithdata.com"


def frame(fig, title, subtitle, top=0.8, bottom=0.12, left=0.2, right=0.96):
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right)
    W, H = fig.get_figwidth() * 72, fig.get_figheight() * 72
    fig.text(18 / W, 1 - 29 / H, title, fontsize=15, fontweight=700, color=INK, ha="left")
    fig.text(18 / W, 1 - 50 / H, subtitle, fontsize=10.5, color=MUTED, ha="left", va="top", linespacing=1.4)
    fig.text(18 / W, 12 / H, SRC, fontsize=8.5, color=MUTED)


def save(fig, name, alt):
    path = os.path.join(CH, name)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    alt = alt.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    s = open(path).read().replace("<svg ", f'<svg role="img" aria-label="{alt}" ', 1)
    open(path, "w").write(s)


# 1. False winners and power by plan ----------------------------------------------------------
r = pd.read_csv(os.path.join(OUT, "ab-test-peeking-sequential-simulation.csv"))
LAB = ["Once, at day 20\n(as planned)", "Weekly", "Every 2 days", "Daily",
       "Daily, with\nO'Brien-Fleming\nboundary", "Daily, with\nPocock boundary"]
COL = [GREY, AMBER, AMBER, RED, BLUE, BLUE]
fig, ax = plt.subplots(figsize=(11.5, 6))
x = np.arange(len(r))
v = r.false_winner_rate * 100
ax.bar(x, v, 0.62, color=COL, zorder=2)
for xi, vi in zip(x, v):
    ax.text(xi, vi + 0.6, f"{vi:.1f}%", ha="center", va="bottom", fontsize=12, fontweight=700, color=INK)
ax.axhline(5, color=INK, lw=1, ls=(0, (3, 3)), zorder=3)
ax.text(5.55, 5, "the 5% you\nsigned up for", ha="left", va="center", fontsize=9, color=INK)
ax.set_xlim(-0.5, 6.35)
ax.axvspan(3.5, 5.5, color="#eff6ff", zorder=0)
ax.text(4.5, 27.5, "the fix", ha="center", fontsize=10, color=BLUE, fontweight=700)
ax.set_xticks(x, LAB, fontsize=10)
ax.set_ylim(0, 30)
ax.set_yticks([0, 5, 10, 15, 20, 25, 30], [f"{k}%" for k in [0, 5, 10, 15, 20, 25, 30]])
ax.set_ylabel("Tests that declare a false winner")
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.tick_params(axis="x", length=0)
frame(fig, "Check an A/B test every day and 1 in 4 'winners' is pure noise",
      "Share of A/A tests (both versions identical) that hit p < 0.05 at some look and get called a winner.\n"
      "A sequential boundary lets you look daily and keeps false winners at 5%.", top=0.8, bottom=0.2, left=0.08)
save(fig, "ab-test-peeking-false-winners-by-plan.svg",
     "Bar chart of false-winner rates: " + "; ".join(f"{l.replace(chr(10), ' ')} {vi:.1f}%" for l, vi in zip(LAB, v)))

# 2. How a boundary works --------------------------------------------------------------------
p = pd.read_csv(os.path.join(OUT, "ab-test-peeking-example-paths.csv"))
fig, ax = plt.subplots(figsize=(11.5, 6))
ax.plot(p.day, p.fixed_z, color=RED, lw=2, ls=(0, (4, 3)), label="p < 0.05 at every look (z = 1.96)")
ax.plot(p.day, np.minimum(p.obf_z, 6), color=BLUE, lw=2.4, label="O'Brien-Fleming boundary: strict early, relaxed late")
ax.plot(p.day, p.pocock_z, color=AMBER, lw=2, label="Pocock boundary: the same bar at every look")
for k, (c, lw) in enumerate(((INK, 2.2), (GREY, 1.4), (GREY, 1.4))):
    ax.plot(p.day, p[f"path_{k}"].abs(), color=c, lw=lw, marker="o", markersize=3.5, zorder=4)
y0 = p.path_0.abs()
d_cross = int(p.day[(y0 >= p.fixed_z)].iloc[0])
ax.annotate(f"Day {d_cross}: p < 0.05.\nA daily peeker ships it.",
            xy=(d_cross, y0[d_cross - 1]), xytext=(1.2, 3.9), fontsize=9.5, color=INK,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
ax.annotate("...but there was never a\ndifference. By day 20 it has faded.", xy=(20, y0.iloc[-1]), xytext=(15.4, 1.5), va="center",
            fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
ax.set_xlim(0.5, 20.5)
ax.set_ylim(0, 6)
ax.set_xticks([1, 5, 10, 15, 20])
ax.set_xlabel("Day of the test")
ax.set_ylabel("Size of the gap between A and B (|z|)")
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False, fontsize=9.5, labelcolor=INK)
frame(fig, "Random noise wanders over the 1.96 line. A sequential boundary sits above it",
      "Three simulated A/A tests (no real difference). Calling a winner when a line crosses a boundary: the red line catches\n"
      "noise early; the blue and amber boundaries are calibrated so only 5% of A/A tests ever cross them in 20 daily looks.",
      top=0.8, bottom=0.22, left=0.08)
save(fig, "ab-test-peeking-sequential-boundaries.svg",
     f"Line chart of three simulated A/A tests against three stopping boundaries. One test crosses z = 1.96 on day {d_cross} "
     "and fades by day 20; it stays below the O'Brien-Fleming and Pocock boundaries.")
print("charts written to", CH)
