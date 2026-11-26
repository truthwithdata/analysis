#!/usr/bin/env python3
"""Charts for 'Sell in May and go away: does it beat buy-and-hold?' (Truth with Data, Nov 2026).
Usage: python sell-in-may-charts.py DATA_DIR CHART_DIR [RENDER_DIR]
Reads the CSVs written by sell-in-may-analysis.py. Writes:
  * sell-in-may-calendar-heatmap-1871-2026.svg   signature 156-year calendar heatmap (hand-built SVG)
  * sell-in-may-poster-1080x1350.svg / sell-in-may-og-1200x630.svg   poster and share-image sources
    (rendered to 1080x1350 and 1200x630 PNGs with Playwright/headless Chromium; RENDER_DIR defaults to CHART_DIR)
  * four supporting matplotlib charts in the site's house style (Inter, #0f172a ink, #2563eb blue).
Diverging scale: red = real loss, blue = real gain, grey = within half a per cent of zero."""
import json
import os
import sys
from html import escape

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

D, CH = sys.argv[1], sys.argv[2]
RD = sys.argv[3] if len(sys.argv) > 3 else CH
os.makedirs(CH, exist_ok=True)
os.makedirs(RD, exist_ok=True)
INK, MUTED, GRID, BLUE, AMBER, GREY, LBLUE, RED = "#0f172a", "#64748b", "#e2e8f0", "#2563eb", "#d97706", "#94a3b8", "#93c5fd", "#dc2626"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ML = "JFMAMJJASOND"
S = json.load(open(os.path.join(D, "sell-in-may-summary.json")))
m = pd.read_csv(os.path.join(D, "sell-in-may-monthly-returns-1871-2026.csv"))
mav = pd.read_csv(os.path.join(D, "sell-in-may-month-averages.csv"))
hy = pd.read_csv(os.path.join(D, "sell-in-may-half-years-1871-2026.csv"))
per = pd.read_csv(os.path.join(D, "sell-in-may-by-period.csv"))
scen = pd.read_csv(os.path.join(D, "sell-in-may-backtest-scenarios.csv"))
H = S["halves"]
base = scen[(scen.cost_per_switch_pct == 0) & (scen.tax_rate_pct == 0)].iloc[0]
c25 = scen[(scen.cost_per_switch_pct == 0.25) & (scen.tax_rate_pct == 0)].iloc[0]
Y0, Y1 = int(m.year.min()), int(m.year.max())
LASTLAB = f"{MON[int(m.month.iloc[-1]) - 1]} {Y1}"
SRC = "Source: Robert Shiller, US stock market data (S&P Composite, dividends, CPI); FRED (3-month T-bill; NBER commercial paper before 1934). Analysis: truthwithdata.com"

# Diverging bins (monthly real total return, %): 4 red, grey, 4 blue
EDGES = [-8, -4, -2, -0.5, 0.5, 2, 4, 8]
COLS = ["#a51d1d", "#d9393e", "#ef8a8a", "#f8c9c9", "#e6e9ee", "#c4d8f7", "#7fadf0", "#2f6fd6", "#173f8f"]
LABS = ["< −8%", "−8 to −4", "−4 to −2", "−2 to −0.5", "±0.5", "0.5 to 2", "2 to 4", "4 to 8", "> 8%"]


def col(v):
    return COLS[int(np.searchsorted(EDGES, v * 100, side="right"))]


def pct(v, d=1):
    s = f"{abs(v):.{d}f}%"
    return ("+" if v > 0 else "−" if v < 0 else "") + s


grid = {(int(r.year), int(r.month)): r.stock_real for r in m.itertuples()}
# summer year -> did staying in stocks beat cash, May-Oct (nominal)?
stay = {int(r.year): r.summer_excess_over_cash > 0 for r in hy.dropna(subset=["summer_excess_over_cash"]).itertuples()}


def heat_cells(x0, y0, cw, rh, gap=1.0, titles=True, transpose=False):
    """Cells for every month. Normal: rows = years, cols = months. Transposed: cols = years, rows = months."""
    out = []
    for (y, mo), v in grid.items():
        if transpose:
            x, yy, w, h = x0 + (y - Y0) * cw, y0 + (mo - 1) * rh, cw, rh - gap
        else:
            x, yy, w, h = x0 + (mo - 1) * cw, y0 + (y - Y0) * rh, cw - gap, rh
        t = f"<title>{MON[mo - 1]} {y}: {pct(100 * v)}</title>" if titles else ""
        out.append(f'<rect x="{x:.4g}" y="{yy:.5g}" width="{w:.3g}" height="{h:.3g}" fill="{col(v)}">{t}</rect>' if titles else
                   f'<rect x="{x:.5g}" y="{yy:.5g}" width="{w:.3g}" height="{h:.3g}" fill="{col(v)}"/>')
    return "\n".join(out)


def legend(x, y, sw=34, h=10, fs=10, step=None):
    step = step or sw
    out = [f'<text x="{x}" y="{y - 6}" font-size="{fs}" fill="{MUTED}">Monthly real total return</text>']
    for k, (c, lab) in enumerate(zip(COLS, LABS)):
        out.append(f'<rect x="{x + k * step}" y="{y}" width="{sw - 2}" height="{h}" fill="{c}"/>')
    out.append(f'<text x="{x}" y="{y + h + fs + 2}" font-size="{fs}" fill="{INK}">loss</text>')
    out.append(f'<text x="{x + 4.5 * step}" y="{y + h + fs + 2}" font-size="{fs}" fill="{INK}" text-anchor="middle">±0.5%</text>')
    out.append(f'<text x="{x + 9 * step - 2}" y="{y + h + fs + 2}" font-size="{fs}" fill="{INK}" text-anchor="end">gain</text>')
    return "\n".join(out)


def svg_open(w, h, title, desc, idp):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-labelledby="{idp}-t {idp}-d" font-family="Inter, \'Segoe UI\', Arial, sans-serif">\n'
            f'<title id="{idp}-t">{escape(title)}</title>\n<desc id="{idp}-d">{escape(desc)}</desc>\n'
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>\n')


mean_by_m = mav.mean_real_pct.to_numpy()
summer_avg = mean_by_m[4:10].mean()
winter_avg = mean_by_m[[10, 11, 0, 1, 2, 3]].mean()
DESC = (f"Calendar heatmap with one row for each year from {Y0} to {Y1} and one column for each month, coloured by that month's "
        f"real total return on US stocks. May to October is outlined. Average real return per month: "
        + ", ".join(f"{MON[k]} {mean_by_m[k]:.2f}%" for k in range(12))
        + f". Summers (May-Oct) averaged {H['summer_mean_pct']:.1f}% after inflation and winters (Nov-Apr) {H['winter_mean_pct']:.1f}%, "
        f"but stocks still beat cash in {H['summer_stocks_beat_cash_pct']:.0f}% of summers. Switching to T-bills every May returned "
        f"{base.strategy_real_cagr_pct:.1f}% a year after inflation from {Y0} to {Y1}, against {base.buyhold_real_cagr_pct:.1f}% for buy-and-hold.")


def bars(x0, ybase, cw, scale, fs, labels=True, gap=4):
    """Average real return per month as small bars above the grid columns."""
    out = []
    for k, v in enumerate(mean_by_m):
        hgt = v * scale
        x = x0 + k * cw + gap / 2
        y = ybase - max(hgt, 0)
        c = BLUE if v > 0 else RED
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw - gap:.1f}" height="{abs(hgt):.1f}" fill="{c}" rx="1.5">'
                   f'<title>{MON[k]}: average {v:.2f}% real</title></rect>')
        if labels:
            ty = y - 4 if v > 0 else ybase + abs(hgt) + fs
            out.append(f'<text x="{x0 + k * cw + cw / 2:.1f}" y="{ty:.1f}" font-size="{fs}" fill="{INK}" text-anchor="middle">{v:.1f}</text>')
    out.append(f'<line x1="{x0}" x2="{x0 + 12 * cw}" y1="{ybase}" y2="{ybase}" stroke="{GREY}" stroke-width="1"/>')
    return "\n".join(out)


# 1. Signature heatmap (article, 480 wide) ---------------------------------------------------------------
def heatmap_article():
    W = 480
    x0, cw, rh = 44, 27, 4
    gx1 = x0 + 12 * cw
    top = 150
    gy0 = top + 104
    gh = (Y1 - Y0 + 1) * rh
    Hh = gy0 + gh + 142
    o = [svg_open(W, Hh, f"155 years of US stock returns, month by month ({Y0}-{Y1})", DESC, "simheat")]
    o.append(f'<text x="16" y="30" font-size="20" font-weight="800" fill="{INK}">Is summer really worse for stocks?</text>')
    o.append(f'<text x="16" y="52" font-size="13.5" fill="{MUTED}">Every month of US stock returns since {Y0}, after inflation.</text>')
    o.append(f'<text x="16" y="69" font-size="13.5" fill="{MUTED}">Outlined: May–October, the months "Sell in May" sits out.</text>')
    # verdict chips
    o.append(f'<text x="16" y="96" font-size="13.5" fill="{INK}"><tspan font-weight="700">Nov–Apr</tspan> averaged {H["winter_mean_pct"]:.1f}% real · '
             f'<tspan font-weight="700">May–Oct</tspan> {H["summer_mean_pct"]:.1f}%</text>')
    o.append(f'<text x="16" y="114" font-size="13.5" fill="{INK}">But stocks still beat cash in <tspan font-weight="700">{H["summer_stocks_beat_cash_pct"]:.0f}%</tspan> of summers.</text>')
    # marginal bars
    o.append(f'<text x="16" y="{top + 2}" font-size="12" fill="{MUTED}">Average monthly real return, %</text>')
    o.append(bars(x0, top + 52, cw, 18, 11))
    # column labels
    for k in range(12):
        o.append(f'<text x="{x0 + k * cw + cw / 2:.1f}" y="{gy0 - 8}" font-size="11" font-weight="600" fill="{INK}" text-anchor="middle">{ML[k]}</text>')
    o.append(heat_cells(x0, gy0, cw, rh))
    # May-Oct outline
    o.append(f'<rect x="{x0 + 4 * cw - 1:.1f}" y="{top + 10}" width="{6 * cw + 1:.1f}" height="{gy0 + gh - top - 8}" fill="none" stroke="{INK}" stroke-width="2" rx="3"/>')
    # decade labels and ticks
    for y in range(1880, Y1 + 1, 10):
        yy = gy0 + (y - Y0) * rh
        o.append(f'<text x="{x0 - 6}" y="{yy + 4}" font-size="12" fill="{MUTED}" text-anchor="end">{y}</text>')
        o.append(f'<line x1="{x0 - 3}" x2="{x0}" y1="{yy}" y2="{yy}" stroke="{GREY}"/>')
    o.append(f'<text x="{x0 - 6}" y="{gy0 + 4}" font-size="12" fill="{MUTED}" text-anchor="end">{Y0}</text>')
    # right strip: stocks beat cash that summer?
    sx = gx1 + 8
    for q, w_ in enumerate(["Stocks", "beat", "cash?"]):
        o.append(f'<text x="{sx + 5}" y="{gy0 - 30 + 12 * q}" font-size="11" fill="{MUTED}" text-anchor="start">{w_}</text>')
    for y, won in stay.items():
        yy = gy0 + (y - Y0) * rh
        o.append(f'<rect x="{sx}" y="{yy:.1f}" width="9" height="{rh:.1f}" fill="{INK if won else "#cbd5e1"}">'
                 f'<title>Summer {y}: stocks {"beat" if won else "lost to"} cash</title></rect>')
    # annotations
    ax = sx + 16

    def note(y, text, mo=None):
        yy = gy0 + (y - Y0) * rh + rh / 2
        o.append(f'<line x1="{sx + 9}" x2="{ax - 2}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{GREY}"/>')
        o.append(f'<text x="{ax}" y="{yy + 4:.1f}" font-size="12" fill="{INK}">{text}</text>')

    note(1929, "1929")
    note(1932, "1932")
    note(1987, "1987")
    note(2002, "2002")
    note(2008, "2008")
    note(2020, "2020")
    # 2002 line across grid
    yy = gy0 + (2002 - Y0) * rh
    o.append(f'<line x1="{x0}" x2="{gx1}" y1="{yy}" y2="{yy}" stroke="{INK}" stroke-width="0.8" stroke-dasharray="2 2"/>')
    # footer
    fy = gy0 + gh + 30
    o.append(legend(16, fy, sw=30, fs=12))
    o.append(f'<rect x="300" y="{fy - 1}" width="10" height="10" fill="{INK}"/><text x="315" y="{fy + 8}" font-size="12" fill="{INK}">stocks beat cash</text>')
    o.append(f'<rect x="300" y="{fy + 15}" width="10" height="10" fill="#cbd5e1"/><text x="315" y="{fy + 24}" font-size="12" fill="{INK}">cash won (May–Oct)</text>')
    o.append(f'<text x="16" y="{fy + 52}" font-size="11.5" fill="{MUTED}">S&amp;P Composite total return from monthly average prices,</text>')
    o.append(f'<text x="16" y="{fy + 66}" font-size="11.5" fill="{MUTED}">deflated by CPI, {MON[int(m.month.iloc[0]) - 1]} {Y0}–{LASTLAB}. Dashed line: 2002, when</text>')
    o.append(f'<text x="16" y="{fy + 80}" font-size="11.5" fill="{MUTED}">Bouman &amp; Jacobsen published. Source: Robert Shiller (Yale), FRED.</text>')
    o.append(f'<text x="16" y="{fy + 102}" font-size="12" font-weight="800" fill="{BLUE}" letter-spacing="0.5">TRUTH WITH DATA</text>')
    o.append(f'<text x="{W - 16}" y="{fy + 102}" font-size="11" fill="{MUTED}" text-anchor="end">truthwithdata.com</text>')
    o.append("</svg>\n")
    open(os.path.join(CH, "sell-in-may-calendar-heatmap-1871-2026.svg"), "w").write("\n".join(o))


# 2. Poster 1080 x 1350 ----------------------------------------------------------------------------------
def poster():
    W, Hh = 1080, 1350
    o = [svg_open(W, Hh, "Sell in May and go away? 155 years of data", DESC, "simposter")]
    o.append(f'<rect width="{W}" height="14" fill="{BLUE}"/>')
    o.append(f'<text x="56" y="92" font-size="54" font-weight="800" fill="{INK}">"Sell in May and go away"</text>')
    o.append(f'<text x="56" y="146" font-size="34" font-weight="600" fill="{MUTED}">155 years of US stocks, month by month</text>')
    x0, cw, rh = 104, 36, 5.6
    gy0 = 300
    gh = (Y1 - Y0 + 1) * rh
    o.append(f'<text x="{x0}" y="180" font-size="17" fill="{MUTED}">Average monthly real return, %</text>')
    o.append(bars(x0, 244, cw, 24, 14))
    for k in range(12):
        o.append(f'<text x="{x0 + k * cw + cw / 2:.1f}" y="{gy0 - 10}" font-size="17" font-weight="700" fill="{INK}" text-anchor="middle">{ML[k]}</text>')
    o.append(heat_cells(x0, gy0, cw, rh, gap=1.2, titles=False))
    o.append(f'<rect x="{x0 + 4 * cw - 1.5}" y="{gy0 - 32}" width="{6 * cw + 2}" height="{gh + 36}" fill="none" stroke="{INK}" stroke-width="3" rx="4"/>')
    o.append(f'<text x="{x0 + 7 * cw}" y="{gy0 + gh + 30}" font-size="16" font-weight="700" fill="{INK}" text-anchor="middle">May–Oct: "go away"</text>')
    for y in range(1880, Y1 + 1, 20):
        yy = gy0 + (y - Y0) * rh
        o.append(f'<text x="{x0 - 10}" y="{yy + 6}" font-size="16" fill="{MUTED}" text-anchor="end">{y}</text>')
    o.append(f'<text x="{x0 - 10}" y="{gy0 + 6}" font-size="16" fill="{MUTED}" text-anchor="end">{Y0}</text>')
    yy = gy0 + (2002 - Y0) * rh
    o.append(f'<line x1="{x0}" x2="{x0 + 12 * cw}" y1="{yy}" y2="{yy}" stroke="{INK}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    # right panel
    px = 600

    def stat(y, big, line1, line2="", c=INK):
        o.append(f'<text x="{px}" y="{y}" font-size="60" font-weight="800" fill="{c}">{big}</text>')
        o.append(f'<text x="{px}" y="{y + 36}" font-size="21" fill="{INK}">{line1}</text>')
        if line2:
            o.append(f'<text x="{px}" y="{y + 63}" font-size="21" fill="{INK}">{line2}</text>')

    o.append(f'<text x="{px}" y="236" font-size="22" font-weight="700" fill="{BLUE}" letter-spacing="1">SUMMERS WERE WEAKER</text>')
    stat(312, f"{H['winter_mean_pct']:.1f}% vs {H['summer_mean_pct']:.1f}%", "average real return, Nov–Apr", "vs May–Oct (the gap is not clearly significant)")
    stat(472, f"{H['summer_stocks_beat_cash_pct']:.0f}%", "of summers, stocks still", "beat sitting in cash")
    o.append(f'<text x="{px}" y="636" font-size="22" font-weight="700" fill="{RED}" letter-spacing="1">THE STRATEGY LOSES</text>')
    stat(712, f"{base.strategy_real_cagr_pct:.1f}% vs {base.buyhold_real_cagr_pct:.1f}%", "a year after inflation: switching", "vs buy-and-hold, before any costs")
    stat(872, f"${base.strategy_real_final:,.0f}", f"vs ${base.buyhold_real_final:,.0f}: what $1 in {Y0}", "grew to (in today's money)")
    stat(1032, f"{base.strategy_won_years_pct:.0f}%", f"of {int(base.years_compared)} years in which", "switching beat holding")
    # legend + footer
    o.append(legend(px, 1180, sw=48, h=14, fs=15))
    o.append(f'<text x="56" y="{Hh - 64}" font-size="15" fill="{MUTED}">S&amp;P Composite total return (monthly averages), deflated by CPI, {MON[int(m.month.iloc[0]) - 1]} {Y0} – {LASTLAB}. Cash: T-bills (commercial paper before 1934).</text>')
    o.append(f'<text x="56" y="{Hh - 40}" font-size="15" fill="{MUTED}">Source: Robert Shiller (Yale) US stock market data; FRED. Dashed line: 2002, when Bouman &amp; Jacobsen published.</text>')
    o.append(f'<rect y="{Hh - 22}" width="{W}" height="22" fill="{INK}"/>')
    o.append(f'<text x="56" y="{Hh - 6}" font-size="15" font-weight="800" fill="#ffffff" letter-spacing="1">TRUTH WITH DATA</text>')
    o.append(f'<text x="{W - 56}" y="{Hh - 6}" font-size="15" fill="#ffffff" text-anchor="end">truthwithdata.com</text>')
    o.append("</svg>\n")
    open(os.path.join(RD, "sell-in-may-poster-1080x1350.svg"), "w").write("\n".join(o))


# 3. Open Graph 1200 x 630 --------------------------------------------------------------------------------
def og():
    W, Hh = 1200, 630
    o = [svg_open(W, Hh, "Does Sell in May work?", DESC, "simog")]
    o.append(f'<rect width="{W}" height="12" fill="{BLUE}"/>')
    o.append(f'<text x="48" y="86" font-size="50" font-weight="800" fill="{INK}">Does "Sell in May" beat buy-and-hold?</text>')
    o.append(f'<text x="48" y="140" font-size="30" fill="{INK}">Summers were weaker: <tspan font-weight="800">{H["summer_mean_pct"]:.1f}%</tspan> vs <tspan font-weight="800">{H["winter_mean_pct"]:.1f}%</tspan> real.</text>')
    o.append(f'<text x="48" y="184" font-size="30" fill="{INK}">Switching still lost: <tspan font-weight="800" fill="{RED}">{base.strategy_real_cagr_pct:.1f}%</tspan> a year vs <tspan font-weight="800" fill="{BLUE}">{base.buyhold_real_cagr_pct:.1f}%</tspan>.</text>')
    x0, cw, rh = 96, (W - 96 - 48) / (Y1 - Y0 + 1), 24
    gy0 = 232
    o.append(heat_cells(x0, gy0, cw, rh, gap=1.5, titles=False, transpose=True))
    for k in range(12):
        o.append(f'<text x="{x0 - 10}" y="{gy0 + k * rh + 17}" font-size="15" fill="{INK}" font-weight="{700 if 4 <= k <= 9 else 400}" text-anchor="end">{MON[k]}</text>')
    o.append(f'<rect x="{x0 - 2}" y="{gy0 + 4 * rh - 2}" width="{W - 48 - x0 + 4}" height="{6 * rh + 3}" fill="none" stroke="{INK}" stroke-width="3" rx="3"/>')
    for y in range(1880, Y1 + 1, 20):
        o.append(f'<text x="{x0 + (y - Y0 + 0.5) * cw:.1f}" y="{gy0 + 12 * rh + 22}" font-size="15" fill="{MUTED}" text-anchor="middle">{y}</text>')
    o.append(f'<text x="48" y="{Hh - 22}" font-size="15" fill="{MUTED}">Each cell: one month of US stocks after inflation, {Y0}–{Y1}. Red = loss, blue = gain. Data: Shiller, FRED.</text>')
    o.append(f'<text x="{W - 48}" y="{Hh - 22}" font-size="16" font-weight="800" fill="{BLUE}" text-anchor="end" letter-spacing="1">TRUTH WITH DATA</text>')
    o.append("</svg>\n")
    open(os.path.join(RD, "sell-in-may-og-1200x630.svg"), "w").write("\n".join(o))


heatmap_article()
poster()
og()

# 4. Supporting charts (matplotlib) -------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": ["Inter", "Segoe UI", "Arial", "sans-serif"], "svg.fonttype": "none",
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "axes.labelsize": 11,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "svg.hashsalt": "truthwithdata",
})


def frame(fig, title, subtitle, source=SRC, top=0.8, bottom=0.15, left=0.08, right=0.97):
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right)
    w, h = fig.get_figwidth() * 72, fig.get_figheight() * 72
    fig.text(18 / w, 1 - 29 / h, title, fontsize=15, fontweight=700, color=INK, ha="left")
    fig.text(18 / w, 1 - 50 / h, subtitle, fontsize=10.5, color=MUTED, ha="left", va="top", linespacing=1.4)
    fig.text(18 / w, 10 / h, source, fontsize=8.2, color=MUTED, va="bottom", linespacing=1.35)


def save(fig, name, alt):
    path = os.path.join(CH, name)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    s = open(path).read().replace("<svg ", f'<svg role="img" aria-label="{escape(alt)}" ', 1)
    open(path, "w").write(s)


def style(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


SRC2 = "Source: Robert Shiller, US stock market data; FRED (TB3MS; NBER M13002 before 1934). Analysis: truthwithdata.com"

# 4a. Growth of $1, real, log scale
inm = m.month.isin([11, 12, 1, 2, 3, 4]).to_numpy()


def path(cost):
    v, out, prev = 1.0, [], inm[0]
    for k in range(len(m)):
        if inm[k] != prev:
            v *= 1 - cost
            prev = inm[k]
        v *= 1 + (m.stock_tr[k] if inm[k] else m.cash[k])
        out.append(v)
    return np.array(out)


defl = np.cumprod(1 + m.inflation.to_numpy())
hold = np.cumprod(1 + m.stock_tr.to_numpy()) / defl
sw0, sw25 = path(0) / defl, path(0.0025) / defl
half = np.cumprod(1 + 0.5 * m.stock_tr.to_numpy() + 0.5 * m.cash.to_numpy()) / defl
t = pd.to_datetime(m.date + "-01")
fig, ax = plt.subplots(figsize=(12.4, 6.4))
style(ax)
series = [(hold, BLUE, 2.2, "Buy-and-hold"), (sw0, AMBER, 2.0, "Sell in May, no costs"),
          (sw25, "#92400e", 1.6, "Sell in May, 0.25% costs"), (half, GREY, 1.6, "Half stocks, half cash")]
ly = [y[-1] for y, *_ in series]
for k in range(1, len(ly)):            # keep labels at least a factor 1.45 apart on the log axis
    ly[k] = min(ly[k], ly[k - 1] / 1.45)
for (y, c, lw, lab), yl in zip(series, ly):
    ax.plot(t, y, color=c, lw=lw)
    ax.annotate(f"{lab}: ${y[-1]:,.0f}", (t.iloc[-1], yl), xytext=(8, 0), textcoords="offset points", va="center",
                fontsize=10, color=INK, annotation_clip=False)
ax.set_yscale("log")
ax.set_yticks([1, 10, 100, 1000, 10000])
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.set_ylabel(f"Value of $1 invested in {Y0}, in {Y1} dollars (log scale)")
ax.set_xlim(t.iloc[0], t.iloc[-1] + pd.Timedelta(days=365))
frame(fig, "Sitting out every summer cost far more than it saved",
      f"Real total return, {MON[int(m.month.iloc[0]) - 1]} {Y0} to {LASTLAB}. Sell in May: stocks Nov–Apr, cash May–Oct. Final values in today's dollars.",
      source=SRC2, right=0.98, left=0.08)
fig.subplots_adjust(right=0.78)
save(fig, "sell-in-may-growth-of-1-dollar-real-1871-2026.svg",
     f"Line chart on a log scale. One dollar invested in {Y0} grew to about ${hold[-1]:,.0f} after inflation with buy-and-hold, "
     f"${sw0[-1]:,.0f} switching to cash every May with no costs, ${sw25[-1]:,.0f} with 0.25% costs per switch and ${half[-1]:,.0f} in a constant half-stocks, half-cash mix.")

# 4b. Summer vs winter gap by era with CI
eras = per[per.kind == "era"].set_index("period").loc[["1871-1950", "1951-2001", "2002-2025", "All 1871-2025"]]
fig, ax = plt.subplots(figsize=(12.4, 5.4))
style(ax, "x")
ylab = [f"{p.replace('All ', 'All years ')}\n({int(r.pairs)} years)" for p, r in eras.iterrows()]
yy = np.arange(len(eras))[::-1]
ax.axvline(0, color=INK, lw=1)
for yv, (_, r) in zip(yy, eras.iterrows()):
    ax.plot([r.gap_ci_lo, r.gap_ci_hi], [yv, yv], color=LBLUE, lw=6, solid_capstyle="round")
    ax.plot(r.gap_mean_pts, yv, "o", color=BLUE, ms=10, mec="white", mew=2)
    ax.annotate(f"{r.gap_mean_pts:+.1f} pts  (95% CI {r.gap_ci_lo:+.1f} to {r.gap_ci_hi:+.1f})", (r.gap_ci_hi, yv), xytext=(10, 0),
                textcoords="offset points", va="center", fontsize=10, color=INK)
ax.set_yticks(yy)
ax.set_yticklabels(ylab)
ax.set_xlim(-6, 17)
ax.set_xlabel("Winter (Nov–Apr) minus summer (May–Oct) average real return, percentage points")
frame(fig, "The summer gap was big from 1951 to 2001, absent before and noisy since",
      "Average difference between winter and summer half-year returns, with bootstrap 95% confidence intervals. Right of zero = winter better.",
      source=SRC2, left=0.15, bottom=0.2, top=0.78)
save(fig, "sell-in-may-summer-winter-gap-by-era.svg",
     "Dot chart with confidence intervals. Winter minus summer real return: " + "; ".join(
         f"{p}: {r.gap_mean_pts:+.1f} points (95% CI {r.gap_ci_lo:+.1f} to {r.gap_ci_hi:+.1f})" for p, r in eras.iterrows()))

# 4c. Strategy minus buy-and-hold, by decade
dec = per[per.kind == "decade"].copy()
fig, ax = plt.subplots(figsize=(12.4, 5.6))
style(ax)
x = np.arange(len(dec))
v = dec.strategy_minus_buyhold_real_cagr_pts_no_cost.to_numpy()
ax.bar(x, v, color=[AMBER if q > 0 else BLUE for q in v], width=0.7)
ax.axhline(0, color=INK, lw=1)
for xi, q in zip(x, v):
    ax.text(xi, q + (0.3 if q > 0 else -0.3), f"{q:+.1f}", ha="center", va="bottom" if q > 0 else "top", fontsize=9.5, color=INK)
ax.set_xticks(x)
ax.set_xticklabels([p.replace("s", "s") for p in dec.period], fontsize=9.5)
ax.set_ylabel("Switching minus buy-and-hold, points a year")
ax.set_ylim(min(v) - 1.5, max(v) + 1.5)
nwin = int((v > 0).sum())
frame(fig, f"Switching beat holding in {nwin} of {len(v)} decades, before any costs",
      "Real annual return of 'Sell in May' (cash May–Oct) minus buy-and-hold, by decade of the summer (May to the next April). Amber: switching ahead. 2020s = 2020–2025.",
      source=SRC2, left=0.08, bottom=0.14)
save(fig, "sell-in-may-switch-minus-hold-by-decade.svg",
     "Bar chart of switching minus buy-and-hold real annual return by decade: " + "; ".join(f"{p} {q:+.1f}" for p, q in zip(dec.period, v)))

# 4d. Average return by calendar month with CI
fig, ax = plt.subplots(figsize=(12.4, 5.6))
style(ax)
x = np.arange(12)
mm = mav.mean_real_pct.to_numpy()
cs = [AMBER if 4 <= k <= 9 else BLUE for k in range(12)]
ax.bar(x, mm, color=cs, width=0.62)
ax.errorbar(x, mm, yerr=[mm - mav.ci_lo, mav.ci_hi - mm], fmt="none", ecolor=INK, elinewidth=1, capsize=4)
ax.axhline(0, color=INK, lw=1)
for xi, q, hi in zip(x, mm, mav.ci_hi):
    ax.text(xi, hi + 0.08, f"{q:.2f}", ha="center", va="bottom", fontsize=9.5, color=INK)
ax.set_xticks(x)
ax.set_xticklabels(MON)
ax.set_ylabel("Average real total return, % (95% CI)")
frame(fig, "January has been the strongest month; mid-September to mid-October the weakest",
      f"Average real total return by calendar month, {Y0}–{Y1}, with bootstrap 95% confidence intervals. Amber: May–October. Because prices are monthly averages,\n"
      "each 'month' runs from roughly the middle of the previous month to the middle of this one.", source=SRC2, left=0.08, bottom=0.12, top=0.76)
save(fig, "sell-in-may-average-real-return-by-month.svg",
     "Bar chart of average real return by month: " + ", ".join(f"{MON[k]} {mm[k]:.2f}%" for k in range(12)))
print("charts written to", CH, "and", RD)
