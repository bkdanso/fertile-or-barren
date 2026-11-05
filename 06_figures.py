#!/usr/bin/env python3
"""06_figures.py - draw the paper figures from the processed data and leaderboard.

Plain-language note: makes the three figures for the paper and README:
  fig1_map.png          where the benchmark intrusions are, colored fertile / weak / barren
  fig2_leaderboard.png  each index's score with its uncertainty range, all samples vs cumulates
  fig3_sample_types.png what kinds of samples fertile and barren intrusions are represented by
Figures carry a DRAFT stamp until run with --final (after the authors' verification).
Colors follow the dataviz reference palette (categorical slots 1-3, validated all-pairs).
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
from indices import DISPLAY  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "paper", "figures")
os.makedirs(FIG, exist_ok=True)
FINAL = "--final" in sys.argv
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"
COL = {"BARREN": "#2a78d6", "FERTILE": "#eb6834", "WEAK": "#1baf7a"}
TYPE_COL = {"CUMULATE": "#2a78d6", "UNRESOLVED": "#eb6834", "FINE_GRAINED_DIKE_SILL": "#1baf7a",
            "ALTERED": "#eda100", "CHILLED_MARGIN": "#e87ba4"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})


def stamp(fig):
    if not FINAL:
        fig.text(0.99, 1.0, "DRAFT - not verified", ha="right", va="bottom", fontsize=8, color="#b42318")


def fig_map(intr):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    fig = plt.figure(figsize=(7.2, 3.9))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
    ax.set_global()
    ax.add_feature(cfeature.LAND, facecolor="#efeee9", edgecolor="none")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.3, edgecolor=MUTED)
    for lbl, size, z in [("BARREN", 14, 2), ("WEAK", 26, 3), ("FERTILE", 30, 4)]:
        s = intr[intr["label"] == lbl]
        ax.scatter(s["lon"], s["lat"], s=size, c=COL[lbl], edgecolors=SURF, linewidths=0.8, zorder=z,
                   transform=ccrs.PlateCarree(), label=f"{lbl.title()} ({len(s)})")
    ax.legend(loc="lower left", frameon=False, fontsize=8, labelcolor=INK)
    stamp(fig)
    save(fig, "fig1_map")


def fig_leaderboard(res):
    res = res.sort_values("ALL_auc_w")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2), sharey=True)
    y = np.arange(len(res))
    for ax, st, title in [(axes[0], "ALL", "All sample types"), (axes[1], "CUMULATE", "Cumulates only")]:
        m = res[f"{st}_auc_w"].values
        lo, hi = res[f"{st}_ci_low"].values, res[f"{st}_ci_high"].values
        ok = ~np.isnan(m)
        ax.axvline(0.5, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
        ax.hlines(y[ok], lo[ok], hi[ok], color=INK2, lw=2, zorder=2)
        ax.scatter(m[ok], y[ok], s=36, color=INK, zorder=3, edgecolors=SURF, linewidths=1)
        for yi in y[~ok]:
            ax.text(0.5, yi, "insufficient data", ha="center", va="center", fontsize=7, color=MUTED)
        ax.set_xlim(0, 1)
        ax.set_title(title, loc="left", color=INK, fontsize=9.5)
        ax.set_xlabel("Intrusion-weighted AUC (95% CI)")
        ax.grid(axis="x", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for sp in ["top", "right", "left"]:
            ax.spines[sp].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.text(0.02, -0.9, "works backwards", fontsize=7, color=MUTED, va="center")
        ax.text(0.98, -0.9, "separates fertile", fontsize=7, color=MUTED, va="center", ha="right")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(res["index"].map(DISPLAY))
    axes[0].set_ylim(-1.5, len(res) - 0.5)
    fig.tight_layout()
    stamp(fig)
    save(fig, "fig2_leaderboard")


def fig_types(bench):
    order = ["CUMULATE", "UNRESOLVED", "FINE_GRAINED_DIKE_SILL", "ALTERED", "CHILLED_MARGIN"]
    labels = ["FERTILE", "WEAK", "BARREN"]
    t = bench.groupby(["label", "sample_type"]).size().unstack(fill_value=0).reindex(labels)[order]
    share = t.div(t.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    left = np.zeros(len(share))
    for st in order:
        v = share[st].values
        ax.barh(np.arange(len(share)), v, left=left, height=0.6, color=TYPE_COL[st],
                edgecolor=SURF, linewidth=2, label=st.replace("_", " ").lower())
        for i, (l, w) in enumerate(zip(left, v)):
            if w > 0.07:
                ax.text(l + w / 2, i, f"{w:.0%}", ha="center", va="center", fontsize=7.5, color=INK)
        left += v
    ax.set_yticks(np.arange(len(share)))
    ax.set_yticklabels([f"{lbl.title()} (n={t.loc[lbl].sum():,})" for lbl in labels])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(ncol=5, loc="upper left", bbox_to_anchor=(0, -0.18), frameon=False, fontsize=7.5)
    stamp(fig)
    save(fig, "fig3_sample_types")


def fig_heatmap(res):
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    cols = [("ALL", "All"), ("CUMULATE", "Cumulate"), ("LIQUID_PROXY", "Chilled margin +\ndike/sill"),
            ("ALTERED", "Altered"), ("UNRESOLVED", "Unresolved")]
    res = res.sort_values("ALL_auc_w", ascending=False)
    M = np.array([[r[f"{c}_auc_w"] for c, _ in cols] for _, r in res.iterrows()], dtype=float)
    # Diverging: orange (works backwards) - neutral gray at 0.5 - blue (separates fertile)
    cmap = LinearSegmentedColormap.from_list("div", ["#c2410c", "#f2c4a8", "#e8e7e3", "#a9c6ee", "#1d5fb4"])
    cmap.set_bad("#fcfcfb")
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    im = ax.imshow(np.ma.masked_invalid(M), cmap=cmap, norm=TwoSlopeNorm(vmin=0.2, vcenter=0.5, vmax=0.8), aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            ax.text(j, i, "n/a" if np.isnan(v) else f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color=MUTED if np.isnan(v) else INK)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([n for _, n in cols], fontsize=8)
    ax.set_yticks(range(len(res)))
    ax.set_yticklabels(res["index"].map(DISPLAY), fontsize=8.5)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(cols)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(res)), minor=True)
    ax.grid(which="minor", color=SURF, linewidth=2)
    ax.tick_params(which="minor", length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, ticks=[0.2, 0.35, 0.5, 0.65, 0.8])
    cb.set_label("Intrusion-weighted AUC", color=INK2, fontsize=8)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5, colors=INK2)
    stamp(fig)
    save(fig, "fig4_auc_by_sample_type")


def save(fig, name):
    for ext, kw in [("png", {"dpi": 300}), ("pdf", {}), ("svg", {})]:
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"), bbox_inches="tight", **kw)
    plt.close(fig)


def fig_map_conus(intr):
    """Figure 1b: benchmark intrusions in the conterminous United States, with USGS deposits for context."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cartopy.io.shapereader as shp
    from shapely.geometry import Point
    from shapely.ops import unary_union
    recs = list(shp.Reader(shp.natural_earth("50m", "cultural", "admin_1_states_provinces_lakes")).records())
    conus = unary_union([r.geometry for r in recs if r.attributes.get("admin") == "United States of America"
                         and r.attributes.get("name") not in ("Alaska", "Hawaii")])
    other = unary_union([r.geometry for r in recs if r.attributes.get("admin") in ("Canada", "Mexico")])

    def in_conus(lon, lat):
        if pd.isna(lon) or pd.isna(lat):
            return False
        pt = Point(lon, lat)
        return conus.distance(pt) < 0.6 and not other.contains(pt) and conus.distance(pt) < other.distance(pt)

    s = intr[[in_conus(x, y) for x, y in zip(intr.lon, intr.lat)]].copy()
    cm = pd.read_excel(os.path.join(ROOT, "data", "raw", "usgs_critical_minerals_v3",
                                    "critical_mineral_deposits_all_tables_v3.xlsx.xlsx"), sheet_name="2026_CM_deposits")
    cm = cm[cm["DepType"].astype(str).str.contains(r"Nickel-copper-PGE|PGE \(low sulfide\)")]
    cm = cm[~cm["Deposit_na"].astype(str).str.contains("placer|Bench", case=False)]
    cm["lat"] = pd.to_numeric(cm["Lat_WGS84"], errors="coerce")
    cm["lon"] = pd.to_numeric(cm["Long_WGS84"], errors="coerce")
    cm = cm[[in_conus(x, y) for x, y in zip(cm.lon, cm.lat)]]

    proj = ccrs.AlbersEqualArea(central_longitude=-96, central_latitude=37.5, standard_parallels=(29.5, 45.5))
    fig = plt.figure(figsize=(7.2, 4.6))
    ax = fig.add_subplot(1, 1, 1, projection=proj)
    ax.set_extent([-121, -46, 24.5, 50.8], crs=ccrs.PlateCarree())
    # Fit the figure to the map aspect so the map sits centered inside a padded outer border.
    x0, x1, y0, y1 = ax.get_extent()
    W, M = 7.2, 0.22
    H = (W - 2 * M) * (y1 - y0) / (x1 - x0) + 2 * M
    fig.set_size_inches(W, H)
    ax.set_position([M / W, M / H, 1 - 2 * M / W, 1 - 2 * M / H])
    ax.spines["geo"].set_visible(False)
    from matplotlib.patches import Rectangle
    fig.patches.append(Rectangle((0.004, 0.004), 0.992, 0.992, transform=fig.transFigure, fill=False,
                                 edgecolor=MUTED, linewidth=0.8))
    ax.add_feature(cfeature.LAND, facecolor="#f6f5f2", edgecolor="none")
    ax.add_geometries([conus], crs=ccrs.PlateCarree(), facecolor="#e9e8e2", edgecolor="none", zorder=1)
    ax.add_feature(cfeature.LAKES, facecolor=SURF, edgecolor=MUTED, linewidth=0.3, zorder=1.5)
    ax.add_feature(cfeature.STATES, edgecolor="#c9c8c2", linewidth=0.35)
    ax.add_feature(cfeature.BORDERS, edgecolor=MUTED, linewidth=0.5)
    ax.add_feature(cfeature.COASTLINE, edgecolor=MUTED, linewidth=0.4)
    pc = ccrs.PlateCarree()
    ax.scatter(cm["lon"], cm["lat"], marker="+", s=28, c=INK2, linewidths=0.9, zorder=3, transform=pc,
               label=f"USGS Ni-Cu-PGE / PGE deposit ({len(cm)})")
    for lbl, size, z in [("BARREN", 30, 4), ("WEAK", 40, 5), ("FERTILE", 52, 6)]:
        t = s[s["label"] == lbl]
        if len(t):
            ax.scatter(t["lon"], t["lat"], s=size, c=COL[lbl], edgecolors=SURF, linewidths=0.9, zorder=z,
                       transform=pc, label=f"{lbl.title()} intrusion ({len(t)})")
    # Direct labels at fixed map positions (lon, lat) with leader lines; intrusions sharing one generalized
    # GEOROC coordinate are labeled together.
    place = {"STILLWATER": (-113.5, 47.6, "right"), "DULUTH": (-97.0, 49.0, "right"),
             "BLUE DRAW": (-101.0, 42.4, "left"), "FISHER LAKE": (-118.0, 41.6, "left"),
             "RAGGEDY MOUNTAIN GABBRO GROUP": (-94.0, 37.3, "left"),
             "MELLEN": (-87.0, 50.3, "left"),
             "BEAN BROOK GABBRO": (-64.0, 45.6, "left"), "VINALHAVEN": (-64.0, 44.2, "left"),
             "ONWAY DIKE": (-64.0, 42.8, "left"), "SOUTHEASTERN NEW ENGLAND": (-64.0, 41.4, "left"),
             "HIGGANUM DIKE": (-64.0, 40.0, "left"), "PALISADES": (-64.0, 38.6, "left"),
             "LAMBERTVILLE": (-64.0, 37.2, "left")}
    def nice(k):
        return " ".join(w if w.isupper() and len(w) <= 2 else w.capitalize() for w in k.split()).replace("47th", "47th")
    groups = s.groupby([s.lat.round(2), s.lon.round(2)])
    for (la, lo), g in groups:
        keys = sorted(g["intrusion_key"])
        anchor = next((k for k in keys if k in place), keys[0])
        tx, ty, ha = place.get(anchor, (lo + 2, la + 1, "left"))
        txt = ", ".join(nice(k) for k in keys) + (" *" if len(g) > 1 else "")
        txt = txt.replace("Beaver Bay, ", "Beaver Bay,\n")
        ax.annotate(txt, xy=proj.transform_point(lo, la, pc), xytext=proj.transform_point(tx, ty, pc),
                    textcoords="data", fontsize=6.5, color=INK, ha=ha, va="center", zorder=7,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5, shrinkA=1, shrinkB=3))
    leg = ax.legend(loc="lower right", bbox_to_anchor=(0.995, 0.07), frameon=True, fontsize=6.5, labelcolor=INK,
                    borderpad=0.4, markerscale=0.8, handletextpad=0.4, labelspacing=0.35)
    leg.get_frame().set_facecolor(SURF)
    leg.get_frame().set_edgecolor("#e4e3df")
    ax.text(0.993, 0.015, "* same generalized GEOROC coordinate", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.0, color=MUTED)
    stamp(fig)
    save(fig, "fig1b_map_conus")
    s[["intrusion_key", "label", "confidence", "n_samples", "lat", "lon", "region"]].to_csv(
        os.path.join(ROOT, "paper", "tables", "Fig1b_conus_intrusions.csv"), index=False)
    bs = pd.read_csv(os.path.join(ROOT, "data", "processed", "benchmark_samples.csv"), low_memory=False,
                     usecols=["lat", "lon"]).dropna()
    la1, lo1 = np.radians(bs.lat.values)[:, None], np.radians(bs.lon.values)[:, None]
    la2, lo2 = np.radians(cm.lat.values)[None, :], np.radians(cm.lon.values)[None, :]
    hav = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    cm["km_to_nearest_benchmark_sample"] = (2 * 6371 * np.arcsin(np.sqrt(hav))).min(axis=0).round(1)
    cm[["Deposit_na", "State", "DepType", "lat", "lon", "km_to_nearest_benchmark_sample"]].to_csv(
        os.path.join(ROOT, "paper", "tables", "Fig1b_conus_usgs_deposits.csv"), index=False)


def main():
    intr = pd.read_csv(os.path.join(ROOT, "data", "processed", "intrusions.csv"))
    res = pd.read_csv(os.path.join(ROOT, "leaderboard", "results.csv"))
    bench = pd.read_csv(os.path.join(ROOT, "data", "processed", "benchmark_samples.csv"), low_memory=False,
                        usecols=["label", "sample_type"])
    fig_map(intr)
    fig_map_conus(intr)
    fig_leaderboard(res)
    fig_types(bench)
    fig_heatmap(res)
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
