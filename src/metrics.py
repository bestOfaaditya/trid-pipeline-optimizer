"""Business metrics for a schedule: the numbers that matter to a lender."""

import math

from pipeline import HOURS_PER_DAY, LE_DEADLINE_HOURS


def compute_metrics(schedule, loans):
    by_loan = {l.loan_id: l for l in loans}
    funded = {}
    le_end = {}
    for row in schedule:
        if row["stage"] == "closing_funding":
            funded[row["loan_id"]] = row["end"]
        if row["stage"] == "le_prep":
            le_end[row["loan_id"]] = row["end"]

    total_ext_cost = 0
    total_ext_days = 0
    loans_past_lock = 0
    loans_past_target = 0
    le_violations = 0
    cycle_times = []
    per_loan = []
    principal_past_lock = 0     # $ of loan value that blew its lock
    total_principal = sum(l.principal for l in loans)

    for lid, loan in by_loan.items():
        f = funded[lid]
        cycle_days = (f - loan.app_time) / HOURS_PER_DAY
        cycle_times.append(cycle_days)

        late_h = max(0, f - loan.lock_expiry)
        late_days = math.ceil(late_h / HOURS_PER_DAY)
        ext_cost = late_days * loan.lock_ext_cost_per_day
        total_ext_cost += ext_cost
        total_ext_days += late_days
        if late_days > 0:
            loans_past_lock += 1
            principal_past_lock += loan.principal
        if f > loan.target_close:
            loans_past_target += 1
        if le_end[lid] > loan.app_time + LE_DEADLINE_HOURS:
            le_violations += 1

        per_loan.append({
            "loan_id": lid, "borrower": loan.borrower,
            "type": loan.loan_type,
            "principal": loan.principal,
            "fee_per_day": loan.lock_ext_cost_per_day,
            "cycle_days": round(cycle_days, 1),
            "lock_ext_days": late_days,
            "lock_ext_cost": ext_cost,
            "past_target": f > loan.target_close,
        })

    # Average size of a sacrificed loan vs the book average: the tell for
    # whether a scheduler is value-aware. A value-blind scheduler sacrifices
    # loans at random with respect to size, so this ratio sits near 1.0.
    avg_book = total_principal / len(loans)
    avg_sacrificed = (principal_past_lock / loans_past_lock
                      if loans_past_lock else 0)

    return {
        "total_lock_extension_cost": total_ext_cost,
        "total_lock_extension_days": total_ext_days,
        "loans_past_lock": loans_past_lock,
        "loans_past_target_close": loans_past_target,
        "trid_le_violations": le_violations,
        "avg_cycle_days": round(sum(cycle_times) / len(cycle_times), 1),
        "max_cycle_days": round(max(cycle_times), 1),
        "principal_past_lock": principal_past_lock,
        "avg_sacrificed_principal": round(avg_sacrificed),
        "avg_book_principal": round(avg_book),
        "per_loan": per_loan,
    }


def print_comparison(base_m, opt_m):
    rows = [
        ("Rate-lock extension cost", f"${base_m['total_lock_extension_cost']:,}",
         f"${opt_m['total_lock_extension_cost']:,}"),
        ("Lock extension days", base_m['total_lock_extension_days'],
         opt_m['total_lock_extension_days']),
        ("Loans blowing their lock", base_m['loans_past_lock'],
         opt_m['loans_past_lock']),
        ("Loans past target close", base_m['loans_past_target_close'],
         opt_m['loans_past_target_close']),
        ("TRID LE deadline misses", base_m['trid_le_violations'],
         opt_m['trid_le_violations']),
        ("Avg cycle time (biz days)", base_m['avg_cycle_days'],
         opt_m['avg_cycle_days']),
        ("Loan value past lock", f"${base_m['principal_past_lock']:,}",
         f"${opt_m['principal_past_lock']:,}"),
        ("Avg size of sacrificed loan",
         f"${base_m['avg_sacrificed_principal']:,}",
         f"${opt_m['avg_sacrificed_principal']:,}"),
    ]
    w = 34
    print(f"\n{'Metric':<{w}}{'FIFO baseline':>16}{'CP-SAT':>12}")
    print("-" * (w + 28))
    for name, b, o in rows:
        print(f"{name:<{w}}{str(b):>16}{str(o):>12}")
    saved = base_m['total_lock_extension_cost'] - opt_m['total_lock_extension_cost']
    print("-" * (w + 28))
    print(f"{'Lock-extension $ saved':<{w}}{'':>16}{'$' + format(saved, ','):>12}")

    # markdown version, ready to paste into the README
    print("\nMarkdown (paste into README):\n")
    print("| Metric | FIFO baseline | CP-SAT optimizer |")
    print("|---|---|---|")
    for name, b, o in rows:
        print(f"| {name} | {b} | {o} |")
