"""
Synthetic loan portfolio generator.

Creates a realistic in-flight portfolio: staggered application dates,
rate locks of varying length, purchase loans with contractual close dates
(tight) and refis (looser). All times in business hours from t=0.
"""

import json
import random
from dataclasses import dataclass, asdict

from pipeline import STAGES, HOURS_PER_DAY


@dataclass
class Loan:
    loan_id: str
    borrower: str
    loan_type: str          # "purchase" | "refi"
    app_time: int           # business hour the application was received
    lock_expiry: int        # business hour the rate lock expires
    target_close: int       # contractual / promised close (business hour)
    lock_ext_cost_per_day: int  # $ per business day of lock extension
    durations: dict         # stage_key -> hours for THIS loan


FIRST_NAMES = ["Avery", "Jordan", "Maya", "Diego", "Priya", "Chen", "Fatima",
               "Liam", "Nina", "Omar", "Sofia", "Ethan", "Grace", "Raj",
               "Hana", "Marcus", "Isla", "Tomas", "Zara", "Noah"]
LAST_NAMES = ["Kim", "Patel", "Garcia", "Nguyen", "Okafor", "Brown", "Silva",
              "Hassan", "Mueller", "Rossi", "Ivanov", "Tanaka", "Lopez",
              "Cohen", "Ali", "Park", "Dube", "Novak", "Reyes", "Walsh"]


def generate_portfolio(n_loans: int = 14, seed: int = 42) -> list:
    rng = random.Random(seed)
    loans = []
    for i in range(n_loans):
        loan_type = "purchase" if rng.random() < 0.6 else "refi"
        # applications arrive over the first ~12 business days
        app_time = rng.randint(0, 12 * HOURS_PER_DAY)

        # per-loan task durations drawn from each stage's range
        durations = {s.key: rng.randint(*s.duration_range) for s in STAGES}

        # rough lower bound on cycle time for this loan (critical path-ish)
        work = sum(durations.values())

        if loan_type == "purchase":
            # purchase contracts: 30-40 business day close, 30-35 day locks
            target_close = app_time + rng.randint(30, 40) * HOURS_PER_DAY
            lock_expiry = app_time + rng.randint(28, 35) * HOURS_PER_DAY
            ext_cost = rng.choice([250, 375, 500])   # $/day extension fee
        else:
            target_close = app_time + rng.randint(35, 50) * HOURS_PER_DAY
            lock_expiry = app_time + rng.randint(32, 45) * HOURS_PER_DAY
            ext_cost = rng.choice([150, 250])

        loans.append(Loan(
            loan_id=f"L{i+1:03d}",
            borrower=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            loan_type=loan_type,
            app_time=app_time,
            lock_expiry=lock_expiry,
            target_close=target_close,
            lock_ext_cost_per_day=ext_cost,
            durations=durations,
        ))
    return loans


def save_portfolio(loans, path):
    with open(path, "w") as f:
        json.dump([asdict(l) for l in loans], f, indent=2)


def load_portfolio(path):
    with open(path) as f:
        raw = json.load(f)
    return [Loan(**r) for r in raw]


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    loans = generate_portfolio(n, seed)
    save_portfolio(loans, "data/loans_sample.json")
    print(f"Generated {len(loans)} loans -> data/loans_sample.json")
