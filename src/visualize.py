"""
Gantt charts: one lane per loan, coloured by resource.

Markers per loan:
    |  (black)  application received
    :  (grey)   TRID Loan Estimate deadline (application + 3 business days)
    x  (red)    LE actually delivered, when it lands past the deadline
    v  (red)    rate-lock expiry

Colours are assigned DYNAMICALLY from the resources present in the schedule,
so the legend always matches the staffing you actually ran with. Nothing is
hardcoded to a fixed number of underwriters.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from pipeline import HOURS_PER_DAY, LE_DEADLINE_HOURS

# Fixed colours for the pooled resources
POOL_COLORS = {
    "processor": "#4C9BE8",
    "closer": "#9B59B6",
    "vendor": "#BDC3C7",
    "external": "#BDC3C7",
}

# Palette the underwriters are drawn from, cycled if there are more
# underwriters than colours.
UW_PALETTE = ["#E67E22", "#27AE60", "#16A085", "#D35400", "#C0392B",
              "#2C3E50", "#8E44AD", "#F1C40F", "#1ABC9C", "#7F8C8D"]


def build_color_map(schedule):
    """Assign a colour to every resource label actually present."""
    labels = sorted({r["resource"] for r in schedule})
    uw_labels = sorted([l for l in labels if l.startswith("UW-")],
                       key=lambda s: int(s.split("-")[1]))
    colors = {}
    for lbl in labels:
        if lbl in POOL_COLORS:
            colors[lbl] = POOL_COLORS[lbl]
    for i, lbl in enumerate(uw_labels):
        colors[lbl] = UW_PALETTE[i % len(UW_PALETTE)]
    return colors, uw_labels


def plot_gantt(schedule, loans, title, path):
    by_loan = {l.loan_id: l for l in loans}
    loan_ids = sorted({r["loan_id"] for r in schedule})
    ypos = {lid: i for i, lid in enumerate(loan_ids)}
    colors, uw_labels = build_color_map(schedule)

    # end time of each loan's le_prep task, to detect TRID violations
    le_end = {r["loan_id"]: r["end"] for r in schedule if r["stage"] == "le_prep"}

    fig, ax = plt.subplots(figsize=(14, 0.45 * len(loan_ids) + 2.4))

    for r in schedule:
        ax.barh(ypos[r["loan_id"]],
                (r["end"] - r["start"]) / HOURS_PER_DAY,
                left=r["start"] / HOURS_PER_DAY,
                height=0.6, color=colors.get(r["resource"], "#7F8C8D"),
                edgecolor="white", linewidth=0.4)

    n_violations = 0
    for lid in loan_ids:
        loan = by_loan[lid]
        y = ypos[lid]
        # application received
        ax.plot(loan.app_time / HOURS_PER_DAY, y, marker="|",
                color="black", markersize=10, markeredgewidth=1.6, zorder=6)
        # TRID LE deadline
        deadline = (loan.app_time + LE_DEADLINE_HOURS) / HOURS_PER_DAY
        ax.plot(deadline, y, marker="|", color="#555555",
                markersize=8, markeredgewidth=1.2, alpha=0.7, zorder=6)
        # LE delivered late -> violation
        if le_end.get(lid, 0) > loan.app_time + LE_DEADLINE_HOURS:
            ax.plot(le_end[lid] / HOURS_PER_DAY, y, marker="x", color="red",
                    markersize=7, markeredgewidth=1.8, zorder=7)
            n_violations += 1
        # rate-lock expiry
        ax.plot(loan.lock_expiry / HOURS_PER_DAY, y, marker="v",
                color="red", markersize=7, zorder=5)

    ax.set_yticks(range(len(loan_ids)))
    ax.set_yticklabels([f"{lid} ({by_loan[lid].loan_type})" for lid in loan_ids],
                       fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Business days from t=0")
    ax.set_title(f"{title}   |   TRID LE violations: {n_violations}")
    ax.grid(axis="x", alpha=0.3)

    # legend built from what is actually in this schedule
    handles = []
    for lbl in ["processor", "closer", "vendor"]:
        if lbl in colors:
            handles.append(mpatches.Patch(color=colors[lbl], label=lbl))
    for lbl in uw_labels:
        handles.append(mpatches.Patch(color=colors[lbl], label=lbl))
    handles += [
        plt.Line2D([0], [0], marker="|", color="w", markeredgecolor="black",
                   markersize=9, label="application"),
        plt.Line2D([0], [0], marker="|", color="w", markeredgecolor="#555555",
                   markersize=9, label="LE deadline"),
        plt.Line2D([0], [0], marker="x", color="w", markeredgecolor="red",
                   markersize=8, label="LE late (TRID)"),
        plt.Line2D([0], [0], marker="v", color="w", markerfacecolor="red",
                   markersize=8, label="lock expiry"),
    ]
    ncol = max(3, min(6, len(handles) // 2))
    ax.legend(handles=handles, loc="upper center",
              bbox_to_anchor=(0.5, -0.12), fontsize=7, ncol=ncol, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Gantt saved -> {path}")
