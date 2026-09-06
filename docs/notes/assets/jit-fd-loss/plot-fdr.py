"""Replot FD-Loss v1 Table F.4. Requires matplotlib (tested with 3.11.1).

Run: python plot-fdr.py
Source: https://arxiv.org/html/2604.28190v1#A6.T4
Values are published endpoints, not measurements from a new experiment.
"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


root = Path(__file__).resolve().parent
with (root / "table-f4.csv").open(newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "svg.fonttype": "path",
    "svg.hashsalt": "jit-fd-loss-table-f4",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.edgecolor": "#aab2bd",
    "text.color": "#243247",
    "axes.labelcolor": "#243247",
    "xtick.color": "#536174",
    "ytick.color": "#243247",
})

fig, axes = plt.subplots(1, 2, figsize=(10, 5.2), sharex=True, sharey=True)
for ax, key, title, color, marker in zip(
    axes,
    ["fd_inception", "fd_sim"],
    ["After FD-Inception", "After FD-SIM"],
    ["#b24c20", "#007d78"],
    ["D", "s"],
):
    for i, row in enumerate(rows):
        base = float(row["original_50_step"])
        post = float(row[key])
        ax.plot([base, post], [i, i], color=color, alpha=0.55, linewidth=2.2)
        ax.scatter(base, i, s=70, marker="o", facecolors="white",
                   edgecolors="#57657a", linewidths=1.6, zorder=3,
                   label="Original 50-step" if i == 0 else None)
        ax.scatter(post, i, s=50, color=color, marker=marker, zorder=4,
                   label="One-step endpoint" if i == 0 else None)
    ax.set_title(title, loc="left", pad=17, fontsize=14, fontweight="bold")
    ax.set_yticks(range(len(rows)), [row["representation"] for row in rows])
    ax.tick_params(axis="y", length=0, pad=9)
    ax.set_xlim(-1, 29)
    ax.set_ylim(5.6, -0.6)
    ax.set_xticks([0, 10, 20])
    ax.grid(axis="x", color="#e5e9ee", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("FDr · lower is better", labelpad=12)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.17), frameon=False,
              fontsize=10, handletextpad=0.4, borderaxespad=0)

fig.subplots_adjust(left=0.14, right=0.98, top=0.88, bottom=0.24, wspace=0.16)
fig.savefig(root / "representation-fdr.svg", bbox_inches="tight",
            metadata={"Date": None, "Title": "JiT-L: per-representation FDr",
                      "Description": "Replot of FD-Loss v1 Table F.4; endpoints only."})

# Normalize Matplotlib's trailing spaces for a clean version-control diff.
svg_path = root / "representation-fdr.svg"
svg_path.write_text("\n".join(line.rstrip() for line in
                    svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
                    encoding="utf-8", newline="\n")
