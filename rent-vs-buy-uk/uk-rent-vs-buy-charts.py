#!/usr/bin/env python3
"""Charts for 'Is renting really dead money in the UK?' (Truth with Data, Oct 2026).
Usage: python uk-rent-vs-buy-charts.py OUT_DIR CHART_DIR [LOGO_PNG]
Reads the CSVs written by uk-rent-vs-buy-analysis.py. House style matches the site's
existing charts: Inter, #0f172a ink, #64748b secondary, #e2e8f0 grid, blue #2563eb,
amber #d97706, grey #94a3b8 for reference marks."""
import sys, os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

OUT, CH = sys.argv[1], sys.argv[2]
LOGO = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(CH, exist_ok=True)
INK, MUTED, GRID, BLUE, AMBER, GREY = "#0f172a", "#64748b", "#e2e8f0", "#2563eb", "#d97706", "#94a3b8"
plt.rcParams.update({
    "font.family": ["Inter", "Segoe UI", "Arial", "sans-serif"], "svg.fonttype": "none",
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "axes.labelsize": 11,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
    "svg.hashsalt": "truthwithdata",
})
SRC = ("Source: HM Land Registry UK HPI (Jul 2026); ONS Price Index of Private Rents (Oct 2026 release); "
       "Bank of England quoted rates. Analysis: truthwithdata.com")
summ = json.load(open(os.path.join(OUT, "summary.json")))
GP, GR, R90 = summ["g_price"], summ["g_rent"], summ["rate90"]
reg = pd.read_csv(os.path.join(OUT, "uk-rent-vs-buy-breakeven-by-region-2026.csv"))
SHORT = {"Yorkshire and The Humber": "Yorkshire & Humber", "East of England": "East of England"}

def frame(fig, title, subtitle, source=SRC, top=0.83, bottom=0.11, left=0.2, right=0.97):
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right)
    fig.text(18 / (fig.get_figwidth() * 72), 1 - 29 / (fig.get_figheight() * 72), title,
             fontsize=15, fontweight=700, color=INK, ha="left")
    fig.text(18 / (fig.get_figwidth() * 72), 1 - 50 / (fig.get_figheight() * 72), subtitle,
             fontsize=10.5, color=MUTED, ha="left", va="top", linespacing=1.4)
    fig.text(18 / (fig.get_figwidth() * 72), 12 / (fig.get_figheight() * 72), source, fontsize=8.5, color=MUTED)

def save(fig, name, alt):
    path = os.path.join(CH, name)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    s = open(path).read().replace("<svg ", f'<svg role="img" aria-label="{alt}" ', 1)
    open(path, "w").write(s)

# 1. Break-even years by region under three scenarios -------------------------------
d = reg[(reg.property_type == "all") & (reg.deposit_pct == 10)].sort_values("breakeven_years", ascending=False)
fig, ax = plt.subplots(figsize=(12.4, 7.4))
y = np.arange(len(d))
CAP = 30
def capped(v): return np.where(np.isnan(v), CAP + 1.2, v)
for col, c, mk, lab in [("breakeven_years", BLUE, "o", f"Prices keep rising {GP:.1f}% a year (2005-26 pace)"),
                        ("breakeven_years_rate_plus_1pt", AMBER, "D", f"...and mortgage rates 1 point higher ({R90+1:.2f}%)"),
                        ("breakeven_years_flat_prices", GREY, "s", "House prices flat (0% a year)")]:
    v = d[col].to_numpy(float)
    ax.scatter(capped(v), y, s=70, color=c, marker=mk, zorder=3, edgecolor="white", linewidth=1.5, label=lab)
for yi, (a, b) in enumerate(zip(d.breakeven_years, capped(d.breakeven_years_flat_prices.to_numpy(float)))):
    ax.plot([a, b], [yi, yi], color=GRID, lw=2, zorder=1)
    ax.text(a - 0.45, yi, f"{a:.1f}", ha="right", va="center", fontsize=9, color=INK)
    fv = d.breakeven_years_flat_prices.iloc[yi]
    ax.text(b + 0.55, yi, "30+" if np.isnan(fv) else f"{fv:.0f}", ha="left", va="center", fontsize=9, color=MUTED)
ax.set_yticks(y, [SHORT.get(r, r) for r in d.region])
ax.set_xlim(-1.2, 34)
ax.set_xticks([0, 5, 10, 15, 20, 25, 30], ["0", "5", "10", "15", "20", "25", "30"])
ax.axvline(CAP + 1.2, color=GRID, lw=1, ls=(0, (2, 2)))
ax.text(CAP + 1.2, len(d) - 0.35, "no break-even\nwithin 30 years", ha="center", va="bottom", fontsize=8.5, color=MUTED)
ax.set_xlabel("Years until buying the average home beats renting it")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.1), ncol=3, frameon=False, fontsize=9.5, labelcolor=INK)
frame(fig, "Buying wins quickly if prices keep rising, and slowly or never if they don't",
      f"Years for a first-time buyer with a 10% deposit ({R90:.2f}% two-year fix at 90% LTV, Sep 2026) to overtake a renter who invests\n"
      "the same cash at 5% a year. Average home of all property types, July 2026 prices and rents.", top=0.84, bottom=0.17)
save(fig, "rent-vs-buy-breakeven-years-by-region-uk-2026.svg",
     f"Dot plot of break-even years by UK region under three scenarios: {d.breakeven_years.min():.1f} to {d.breakeven_years.max():.1f} "
     f"years if prices keep rising 3% a year, {d.breakeven_years_rate_plus_1pt.min():.1f} to {d.breakeven_years_rate_plus_1pt.max():.1f} "
     f"years if mortgage rates are a point higher, and {d.breakeven_years_flat_prices.min():.0f} years to more than 30 if prices are flat.")

# 2. First-year cost of owning vs rent (monthly) --------------------------------------
fc = pd.read_csv(os.path.join(OUT, "uk-rent-vs-buy-first-year-costs-2026.csv"))
fc = fc[fc.region != "United Kingdom"].copy()
fc["mi"] = fc.maintenance + fc.insurance
fc = fc.sort_values("rent_year1")
fig, ax = plt.subplots(figsize=(12.4, 7.6))
y = np.arange(len(fc))
left = np.zeros(len(fc))
for col, c, lab in [("interest", BLUE, "Mortgage interest"), ("mi", "#93c5fd", "Maintenance (1% of value) and buildings insurance"),
                    ("opportunity_cost", GREY, "Return forgone on deposit and buying costs (5%)")]:
    w = fc[col].to_numpy() / 12
    ax.barh(y, w, left=left, height=0.62, color=c, edgecolor="white", linewidth=2, label=lab)
    left += w
net = fc.net_cost_of_owning.to_numpy() / 12
rent = fc.rent_year1.to_numpy() / 12
ax.scatter(rent, y, marker="D", s=70, color=AMBER, edgecolor="white", linewidth=1.5, zorder=4, label="Rent for the same average home")
ax.scatter(net, y, marker="|", s=320, color=INK, linewidth=2.5, zorder=4, label=f"Cost of owning after {GP:.1f}% expected price growth")
for yi in range(len(fc)):
    ax.text(left[yi] + 40, yi, f"£{left[yi]:,.0f} vs £{rent[yi]:,.0f} rent", va="center", fontsize=9, color=INK)
ax.set_yticks(y, [SHORT.get(r, r) for r in fc.region])
ax.set_xlim(0, 3900)
ax.set_xticks(range(0, 3501, 500), [f"£{v:,}" for v in range(0, 3501, 500)])
ax.set_xlabel("Per month, first year of ownership")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
ax.legend(loc="lower right", frameon=False, fontsize=9.5, labelcolor=INK)
frame(fig, "Before house-price growth, owning costs more than renting in every region",
      "Unrecoverable first-year costs of owning the average home with a 10% deposit, against the rent on the same home. Capital repayment\n"
      "is excluded because it becomes equity; one-off buying and selling costs are excluded here but included in the break-even model.")
save(fig, "first-year-cost-of-owning-vs-rent-by-region-uk-2026.svg",
     "Stacked bars of monthly first-year owning costs by region: mortgage interest alone is 77% to 107% of rent, and interest plus "
     "maintenance, insurance and forgone returns exceeds rent everywhere; after expected price growth owning is cheaper than rent.")

# 3. Sensitivity heatmap: mortgage rate x price growth (median region) ------------------
s = pd.read_csv(os.path.join(OUT, "uk-rent-vs-buy-sensitivity-2026.csv"))
t = s[s.table == "rate_x_price_growth"].pivot(index="mortgage_rate_pct", columns="price_growth_pct",
                                               values="median_breakeven_years").sort_index(ascending=False)
cmap = LinearSegmentedColormap.from_list("b", ["#eff6ff", "#93c5fd", "#2563eb", "#1e3a8a"])
fig, ax = plt.subplots(figsize=(10.6, 7.2))
vals = t.to_numpy(float)
ax.imshow(np.where(np.isnan(vals), 31, np.minimum(vals, 31)), cmap=cmap, vmin=0, vmax=31, aspect="auto")
for i in range(vals.shape[0]):
    for j in range(vals.shape[1]):
        v = vals[i, j]; shade = 31 if np.isnan(v) else min(v, 31)
        ax.text(j, i, "30+" if np.isnan(v) else (f"{v:.1f}" if v < 10 else f"{v:.0f}"), ha="center", va="center",
                fontsize=10.5, color="white" if shade > 12 else INK, fontweight=600)
ri = list(t.index).index(R90); ci = [round(c, 2) for c in t.columns].index(round(GP, 2))
ax.add_patch(plt.Rectangle((ci - 0.5, ri - 0.5), 1, 1, fill=False, ec=AMBER, lw=3))
ax.set_xticks(range(len(t.columns)), [f"{c:.1f}%" + ("\n(2005-26)" if abs(c - GP) < 0.01 else "") for c in t.columns])
ax.set_yticks(range(len(t.index)), [f"{r:.2f}%" + (" (Sep 2026)" if abs(r - R90) < 0.001 else "") for r in t.index])
ax.set_xlabel("House-price growth, % a year"); ax.set_ylabel("Mortgage rate (2-year fix, 90% LTV)")
for sp in ax.spines.values(): sp.set_visible(False)
ax.tick_params(length=0)
frame(fig, "House-price growth matters more than anything else in the model",
      "Median break-even in years across 12 UK regions, first-time buyer with a 10% deposit; renter invests at 5%, rents rise 3.0% a year.\n"
      "Outlined cell = today's rate and the 2005-26 price trend. '30+' = buying has not caught up after 30 years in the median region.",
      left=0.2, right=0.97, top=0.83, bottom=0.13)
save(fig, "rent-vs-buy-breakeven-sensitivity-mortgage-rate-price-growth.svg",
     "Heatmap of median break-even years by mortgage rate (3% to 7%) and house-price growth (0% to 5%). At today's rate it is "
     f"{vals[ri, ci]:.1f} years with 3% price growth, {vals[ri, 2]:.1f} years with 2%, {vals[ri, 1]:.0f} years with 1% and "
     f"{vals[ri, 0]:.0f} years with flat prices.")

# 4. Backtest heatmap: buy year x years held (median across regions, 5% return) --------
bt = pd.read_csv(os.path.join(OUT, "uk-rent-vs-buy-backtest-2005-2026.csv"))
b = bt[bt.return_assumption == "fixed_5pct"]
med = b.groupby(["buy_year", "years_held"]).gap_pct_of_price.median().unstack()
fig, ax = plt.subplots(figsize=(12.4, 8.0))
divc = LinearSegmentedColormap.from_list("d", [AMBER, "#fde68a", "#f1f5f9", "#93c5fd", BLUE])
M = med.to_numpy(float)
im = ax.imshow(M, cmap=divc, norm=TwoSlopeNorm(vcenter=0, vmin=-30, vmax=60), aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        if not np.isnan(M[i, j]) and (j + 1) in (1, 2, 3, 5, 10, 15, 20):
            ax.text(j, i, f"{M[i, j]:+.0f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(M[i, j]) > 35 else INK)
ax.set_xticks(range(M.shape[1]), [str(c) for c in med.columns], fontsize=9)
ax.set_yticks(range(M.shape[0]), [str(r) for r in med.index], fontsize=9)
ax.set_xlabel("Years held (sold in July)"); ax.set_ylabel("Year bought (July)")
for sp in ax.spines.values(): sp.set_visible(False)
ax.tick_params(length=0)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, ticks=[-30, -15, 0, 15, 30, 45, 60])
cb.ax.set_yticklabels(["-30%", "-15%", "0", "+15%", "+30%", "+45%", "+60%"], fontsize=8.5)
cb.set_label("Renter ahead  <  0  <  buyer ahead", fontsize=9, color=MUTED)
cb.outline.set_visible(False)
frame(fig, "Most buyers since 2005 came out ahead, but not those who bought in 2006-08 or in 2022-24",
      "Buyer's net wealth minus renter's at sale, % of purchase price; median of the regions with data for that year (9 English regions from\n"
      "2005, Wales 2009, Scotland 2011, NI 2015). 25% deposit, actual prices, rents and 2-year fixed rates; renter invests at 5% a year.",
      left=0.08, right=0.93, top=0.85, bottom=0.1)
save(fig, "rent-vs-buy-historical-backtest-buy-year-years-held-2005-2026.svg",
     "Heatmap of buyer-minus-renter wealth by purchase year and years held, 2005 to 2026. Buyers in 2006 to 2008 were behind for "
     "up to a decade; buyers from 2009 to 2021 were mostly well ahead after five years; buyers in 2022 to 2024 were behind after two years.")

# 5. Net wealth paths, one region ------------------------------------------------------
# Re-use the model exactly as defined in the analysis script (sections 1-3 only, no data loading)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "uk-rent-vs-buy-analysis.py")).read()
ns = {"__name__": "rvb_model"}
exec(src.split("# 4. Load data")[0].replace("RAW = sys.argv", "RAW = [None, None]").replace("OUT = sys.argv", "OUT = [None, None, None]")
     .replace("os.makedirs(OUT, exist_ok=True)", ""), ns)
class _M: pass
m = _M(); m.run_forward = ns["run_forward"]
r = reg[(reg.region == "West Midlands") & (reg.property_type == "all") & (reg.deposit_pct == 10)].iloc[0]
fig, ax = plt.subplots(figsize=(12.4, 7.0))
yrs = np.arange(0, 361) / 12
ends = []
for gp, ls, lab in [(GP, "-", f"prices +{GP:.1f}%/yr"), (0.0, (0, (4, 3)), "flat prices")]:
    bw, rw = m.run_forward(r.price_jul2026, r.monthly_rent_jul2026, R90, gp, GR, 5.0, 10, "england", False, "E12000005")
    ax.plot(yrs, bw / 1000, color=BLUE, lw=2, ls=ls, label=f"Buyer, {lab}")
    ax.plot(yrs, rw / 1000, color=AMBER, lw=2, ls=ls, label=f"Renter, {lab}")
    if gp == GP:
        k = int(round(ns["breakeven_years"](bw, rw) * 12))
        ax.scatter([yrs[k]], [bw[k] / 1000], s=60, color=INK, zorder=5)
        ax.annotate(f"Break-even after {yrs[k]:.1f} years", (yrs[k], bw[k] / 1000), xytext=(yrs[k] + 2.5, bw[k] / 1000 + 90),
                    fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ends += [bw[-1] / 1000, rw[-1] / 1000]
ys = sorted(ends)
pos = []
for v in ys:
    pos.append(max(v, pos[-1] + 22) if pos else v)
for v, p_ in zip(ys, pos):
    ax.text(30.3, p_, f"£{v:,.0f}k", va="center", fontsize=9, color=INK)
ax.set_xlim(0, 32.5); ax.set_xticks(range(0, 31, 5))
ax.set_xlabel("Years after buying"); ax.set_ylabel("Net wealth, £ thousand (nominal)")
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9.5, labelcolor=INK)
frame(fig, "One home, two price paths: with flat prices the buyer never catches the renter",
      f"West Midlands average home (£{r.price_jul2026:,.0f}; rent £{r.monthly_rent_jul2026:,.0f} a month). Buyer: 10% deposit, {R90:.2f}% "
      "re-fixed every two years, 25-year repayment. Renter: invests the\ndeposit, the buying costs and any monthly saving at 5% a year. "
      "Buyer's wealth is net of mortgage and selling costs.", left=0.08, right=0.95)
save(fig, "rent-vs-buy-net-wealth-over-time-west-midlands.svg",
     "Line chart of buyer and renter net wealth over 30 years for the average West Midlands home. With 3% price growth the buyer "
     "overtakes after 3 years and ends far ahead; with flat prices the buyer stays behind the renter for the whole 30 years.")

# 6. Local authorities -----------------------------------------------------------------
la = pd.read_csv(os.path.join(OUT, "uk-rent-vs-buy-breakeven-by-local-authority-2026.csv"))
order = la.assign(b=la.breakeven_years.fillna(np.inf)).groupby("region").b.median().sort_values(ascending=False).index
fig, ax = plt.subplots(figsize=(12.4, 7.6))
rng = np.random.default_rng(7)
for yi, rg in enumerate(order):
    v = la[la.region == rg].breakeven_years.to_numpy(float)
    x = np.where(np.isnan(v), CAP + 1.2, v)
    ax.scatter(x, yi + rng.uniform(-0.22, 0.22, len(x)), s=22, color=BLUE, alpha=0.55, edgecolor="none")
    med_ = np.median(np.where(np.isnan(v), np.inf, v))
    ax.plot([med_, med_], [yi - 0.33, yi + 0.33], color=INK, lw=2.2)
    ax.text(33.2, yi, f"{np.mean(v <= 5) * 100:.0f}%", va="center", ha="center", fontsize=9, color=INK)
ax.text(33.2, len(order) - 0.35, "LAs under\n5 years", ha="center", va="bottom", fontsize=8.5, color=MUTED)
for name in ["Newcastle upon Tyne", "Manchester", "Elmbridge", "Powys", "Derbyshire Dales", "Bristol, City of", "Richmond upon Thames"]:
    row = la[la.local_authority == name].iloc[0]
    yi = list(order).index(row.region); xv = CAP + 1.2 if np.isnan(row.breakeven_years) else row.breakeven_years
    ax.annotate(name.replace(", City of", ""), (xv, yi), xytext=(0, 12), textcoords="offset points", fontsize=8.5,
                color=MUTED, ha="center")
ax.axvline(CAP + 1.2, color=GRID, lw=1, ls=(0, (2, 2)))
ax.set_yticks(range(len(order)), [SHORT.get(r, r) for r in order])
ax.set_xlim(-0.5, 35); ax.set_xticks([0, 5, 10, 15, 20, 25, 30, CAP + 1.2], ["0", "5", "10", "15", "20", "25", "30", "30+"])
ax.set_xlabel("Break-even years, average home in each local authority (bar = regional median)")
ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
frame(fig, "Cities with high rents relative to prices favour buying; expensive rural and commuter areas favour renting",
      f"{len(la)} local authorities in England and Wales, July 2026 prices and rents, baseline assumptions (10% deposit, {R90:.2f}%, prices +{GP:.1f}%/yr,\n"
      f"renter invests at 5%). All property types; comparing like-for-like terraced houses shortens most break-evens (median "
      f"{la.breakeven_years_terraced.median():.1f} vs {la.breakeven_years.fillna(np.inf).median():.1f} years).")
save(fig, "rent-vs-buy-breakeven-by-local-authority-england-wales-2026.svg",
     "Strip plot of break-even years for 316 local authorities grouped by region. Most cities break even within 1 to 3 years; "
     "15 high-priced rural and commuter authorities such as Elmbridge and Powys do not break even within 30 years.")

# 7. Open Graph image 1200x630 PNG -----------------------------------------------------
d = reg[(reg.property_type == "all") & (reg.deposit_pct == 10)].sort_values("breakeven_years")
fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor("white")
fig.text(0.05, 0.86, "Is renting really 'dead money' in the UK?", fontsize=29, fontweight=800, color=INK)
fig.text(0.05, 0.77, "Original analysis of 12 regions and 316 local authorities, with a 2005-2026 backtest", fontsize=15, color=MUTED)
fig.text(0.05, 0.56, f"{d.breakeven_years.min():.1f}-{d.breakeven_years.max():.1f} yrs", fontsize=46, fontweight=800, color=BLUE)
fig.text(0.05, 0.47, f"to break even if prices keep rising {GP:.1f}% a year", fontsize=15, color=INK)
fv = d.breakeven_years_flat_prices
fig.text(0.05, 0.30, f"{fv.min():.0f}-30+ yrs", fontsize=46, fontweight=800, color=AMBER)
fig.text(0.05, 0.21, "if house prices stay flat", fontsize=15, color=INK)
fig.text(0.05, 0.07, "truthwithdata.com  ·  Rent vs Buy Calculator inside", fontsize=13, color=MUTED)
ax = fig.add_axes([0.6, 0.12, 0.36, 0.58])
ax.barh(range(len(d)), d.breakeven_years, color=BLUE, height=0.65)
ax.set_yticks(range(len(d)), [SHORT.get(r, r) for r in d.region], fontsize=10)
ax.set_xticks([0, 1, 2, 3, 4]); ax.set_xlabel("Break-even years (baseline)", fontsize=10)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
if LOGO and os.path.exists(LOGO):
    img = plt.imread(LOGO)
    lx = fig.add_axes([0.855, 0.79, 0.12, 0.18]); lx.imshow(img); lx.axis("off")
fig.savefig(os.path.join(CH, "rent-vs-buy-og-1200x630.png"), dpi=100, facecolor="white")
plt.close(fig)
print("charts written to", CH)
