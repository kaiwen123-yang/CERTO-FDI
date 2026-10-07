"""Render only the frozen figure data beside this script.

Requirements: matplotlib and Pillow. The input is exact rational certificate
data, not measurements. This does not run the science scan or modify its data.
"""
from pathlib import Path
from fractions import Fraction
import argparse
import hashlib
import json

parser = argparse.ArgumentParser()
parser.add_argument("--export", action="store_true")
args = parser.parse_args()
OUT = Path(__file__).resolve().parent
data_path = OUT / "d2a_readout_figure_data_v1.json"
data = json.loads(data_path.read_text(encoding="utf-8"))
assert data["complete_subset"] and not data["full_400_table_claimed_complete"]
groups = {}
for readout in data["readouts"]:
    groups[readout] = sorted(
        (r for r in data["rows"] if r["readout"] == readout and r["Vplus"]),
        key=lambda r: int(r["H_post_slots"]))
    assert [int(r["H_post_slots"]) for r in groups[readout]] == [60, 80, 100, 120, 160, 200]

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

plt.rcParams.update({
    "font.family": "Arial", "font.size": 8, "axes.labelsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "axes.linewidth": .6, "xtick.major.width": .6, "ytick.major.width": .6,
})
fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.9))
fig.subplots_adjust(left=.073, right=.98, bottom=.23, top=.91, wspace=.30)
styles = {
    "average250": dict(color="#0072B2", marker="s", linestyle="-", label="250-sample average"),
    "point_last_fast_read": dict(color="#D55E00", marker="o", linestyle="--",
                                  markerfacecolor="white", label="Last existing point"),
}
for readout, rows in groups.items():
    x = [float(Fraction(r["elapsed_seconds"])) for r in rows]
    power = [float(Fraction(r["protected_power_lower"])) for r in rows]
    variance = [float(Fraction(r["Vplus"])) for r in rows]
    for ax, y in zip(axes, [power, variance]):
        ax.plot(x, y, linewidth=1.2, markersize=4, **styles[readout])
axes[0].axhline(.9, color=".4", linestyle=":", linewidth=.9)
axes[0].text(29, .84, "Required lower bound: 0.9", color=".3", fontsize=8)
axes[0].set_ylim(-.06, 1.07)
axes[0].set_yticks([0, .25, .5, .75, 1])
axes[0].set_ylabel("Certified power lower bound")
axes[1].set_yscale("log")
axes[1].set_ylim(3e-7, .05)
axes[1].set_yticks([1e-6, 1e-4, 1e-2])
axes[1].set_ylabel("Gaussian-comparator variance bound")
for panel, ax in zip(["(a)", "(b)"], axes):
    ax.set_xlabel("Elapsed physical time including prefix (s)")
    ax.set_xlim(14, 53)
    ax.set_xticks([16, 21, 26, 31, 41, 51])
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(direction="out", length=3)
    ax.text(0, 1.07, panel, transform=ax.transAxes, weight="bold")
    ax.grid(axis="y", color=".9", linewidth=.5)
axes[1].legend(loc="center right", frameon=False, bbox_to_anchor=(1, .51))
fig.text(.5, .025, "H = 60, 80, 100, 120, 160, 200 slots; one frozen calendar family", ha="center")
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
canvas = fig.bbox
outside = []
for artist in fig.findobj(matplotlib.text.Text):
    if not artist.get_visible() or not artist.get_text():
        continue
    box = artist.get_window_extent(renderer)
    if (box.x0 < canvas.x0 - 1 or box.y0 < canvas.y0 - 1 or
        box.x1 > canvas.x1 + 1 or box.y1 > canvas.y1 + 1):
        outside.append(artist.get_text())
assert not outside, outside
preview = OUT / "d2a_readout_figure_preview_v1.png"
fig.savefig(preview, dpi=170, facecolor="white")
Image.open(preview).convert("L").save(OUT / "d2a_readout_figure_grayscale_v1.png")
qa = {
    "data_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
    "plotted_rows": 12, "explicitly_excluded_zero_direction_rows": 2,
    "missing_or_pending_rows_plotted": 0, "texts_outside_canvas": outside,
    "minimum_font_pt": 8, "size_inches": [7.16, 2.9],
    "empirical_CI_or_standard_error": False,
    "human_visual_review": "PENDING",
    "exported_after_visual_review": args.export,
}
if args.export:
    for ext in ["pdf", "svg"]:
        fig.savefig(OUT / ("d2a_readout_figure_v1." + ext), facecolor="white")
    fig.savefig(OUT / "d2a_readout_figure_v1.png", dpi=600, facecolor="white")
    qa["human_visual_review"] = "Root inspected color and grayscale preview before export."
(OUT / "d2a_readout_figure_qa_v1.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
print(json.dumps(qa))
