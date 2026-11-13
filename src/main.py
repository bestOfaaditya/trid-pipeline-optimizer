"""
Run the full experiment: generate portfolio, schedule with FIFO and CP-SAT,
compare business metrics, draw Gantt charts.

Usage:
    python src/main.py [--loans 14] [--seed 42] [--processors 3]
                       [--underwriters 2] [--closers 2] [--time-limit 60]
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from generate import generate_portfolio, save_portfolio
from baseline import fifo_schedule
from metrics import compute_metrics, print_comparison
from visualize import plot_gantt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--loans", type=int, default=14)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--processors", type=int, default=3)
    p.add_argument("--underwriters", type=int, default=2)
    p.add_argument("--closers", type=int, default=2)
    p.add_argument("--time-limit", type=int, default=60)
    p.add_argument("--no-solve", action="store_true",
                   help="run baseline only (no ortools required)")
    args = p.parse_args()

    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    loans = generate_portfolio(args.loans, args.seed)
    save_portfolio(loans, "data/loans_sample.json")
    print(f"Portfolio: {len(loans)} loans "
          f"({sum(l.loan_type == 'purchase' for l in loans)} purchase, "
          f"{sum(l.loan_type == 'refi' for l in loans)} refi)")
    print(f"Staff: {args.processors} processors, {args.underwriters} "
          f"underwriters, {args.closers} closers\n")

    # ---- baseline ----------------------------------------------------------
    base_sched = fifo_schedule(loans, args.processors, args.underwriters,
                               args.closers)
    base_m = compute_metrics(base_sched, loans)
    plot_gantt(base_sched, loans, "FIFO baseline schedule",
               "output/gantt_fifo.png")

    if args.no_solve:
        print("\nBaseline metrics:", {k: v for k, v in base_m.items()
                                      if k != "per_loan"})
        return

    # ---- optimizer ---------------------------------------------------------
    from model import solve_schedule
    opt_sched, _ = solve_schedule(loans, args.processors, args.underwriters,
                                  args.closers, time_limit_s=args.time_limit)
    opt_m = compute_metrics(opt_sched, loans)
    plot_gantt(opt_sched, loans, "CP-SAT optimized schedule",
               "output/gantt_optimized.png")

    with open("output/schedule_optimized.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=opt_sched[0].keys())
        w.writeheader()
        w.writerows(opt_sched)
    print("Schedule CSV -> output/schedule_optimized.csv")

    print_comparison(base_m, opt_m)


if __name__ == "__main__":
    main()
