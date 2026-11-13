"""CP-SAT checks. Skipped when OR-Tools is not installed."""

import pytest

pytest.importorskip("ortools")

from generate import generate_portfolio          # noqa: E402
from metrics import compute_metrics              # noqa: E402
from model import solve_schedule                 # noqa: E402
from validate import check_schedule              # noqa: E402


@pytest.mark.parametrize("n_loans,seed,staff", [
    (8, 42, (3, 2, 2)),      # comfortable staffing
    (12, 42, (3, 1, 2)),     # one underwriter: locks will be missed
    (10, 7, (3, 2, 1)),
])
def test_cpsat_schedule_is_valid_and_never_misses_the_loan_estimate(
        n_loans, seed, staff):
    loans = generate_portfolio(n_loans, seed)
    schedule, _ = solve_schedule(loans, *staff, time_limit_s=20, verbose=False)
    assert check_schedule(schedule, loans, *staff) == []
    assert compute_metrics(schedule, loans)["trid_le_violations"] == 0
