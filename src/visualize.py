"""Gantt charts: one lane per loan, colored by resource, with lock-expiry markers."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from pipeline import HOURS_PER_DAY

COLORS = {
    "processor": "#4C9BE8",
    "closer": "#9B59B6",
    "vendor": "#BDC3C7",
    "external": "#BDC3C7",
    "UW-1": "#E67E22",
    "UW-2": "#27AE60",
    "UW-3": "#16A085",
    "UW-4": "#D35400",
}


def plot_gantt(schedule, loans, title, path):
    by_loan = {l.loan_id: l for l in loans}
    loan_ids = sorted({r["loan_id"] for r in schedule})
    ypos = {lid: i for i, lid in enumerate(loan_ids)}

    fig, ax = plt.subplots(figsize=(14, 0.45 * len(loan_ids) + 2))

    for r in schedule:
        color = COLORS.get(r["resource"], "#7F8C8D")
        ax.barh(ypos[r["loan_id"]],
                (r["end"] - r["start"]) / HOURS_PER_DAY,
                left=r["start"] / HOURS_PER_DAY,
                height=0.6, color=color, edgecolor="white", linewidth=0.4)

    # lock expiry markers
    for lid in loan_ids:
        loan = by_loan[lid]
        ax.plot(loan.lock_expiry / HOURS_PER_DAY, ypos[lid], marker="v",
                color="red", markersize=7, zorder=5)

    ax.set_yticks(range(len(loan_ids)))
    ax.set_yticklabels([f"{lid} ({by_loan[lid].loan_type})" for lid in loan_ids],
                       fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Business days from t=0")
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.3)

    legend = [mpatches.Patch(color=c, label=k) for k, c in COLORS.items()
              if k != "external"]
    legend.append(plt.Line2D([0], [0], marker="v", color="w",
                             markerfacecolor="red", markersize=8,
                             label="rate-lock expiry"))
    ax.legend(handles=legend, loc="lower right", fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Gantt saved -> {path}")
