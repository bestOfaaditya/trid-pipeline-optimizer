"""Checks that run without OR-Tools: generator, FIFO baseline, metrics, validator."""

import copy

import pytest

from baseline import fifo_schedule
from generate import generate_portfolio
from metrics import compute_metrics
from pipeline import BASIS_POINT
from validate import check_schedule

STAFF = dict(n_processors=3, n_underwriters=2, n_closers=2)


def closing_row(schedule, loan_id):
    return next(r for r in schedule
                if r["loan_id"] == loan_id and r["stage"] == "closing_funding")


def test_generator_is_deterministic():
    assert generate_portfolio(14, seed=42) == generate_portfolio(14, seed=42)
    assert generate_portfolio(14, seed=42) != generate_portfolio(14, seed=7)


def test_lock_fee_is_basis_points_of_principal():
    for loan in generate_portfolio(30, seed=3):
        expected = round(loan.principal * loan.bps_per_day / BASIS_POINT)
        assert loan.lock_ext_cost_per_day == expected


@pytest.mark.parametrize("n_loans,seed,staff", [
    (14, 42, (3, 2, 2)),
    (30, 42, (3, 1, 2)),
    (20, 7, (2, 3, 1)),
    (15, 1, (4, 5, 5)),
])
def test_fifo_obeys_the_physical_rules(n_loans, seed, staff):
    loans = generate_portfolio(n_loans, seed)
    schedule = fifo_schedule(loans, *staff)
    # FIFO may miss the Loan Estimate deadline, nothing else
    assert check_schedule(schedule, loans, *staff,
                          enforce_le_deadline=False) == []


def test_fifo_default_run_matches_readme():
    loans = generate_portfolio(14, seed=42)
    m = compute_metrics(fifo_schedule(loans, **STAFF), loans)
    assert m["trid_le_violations"] == 12
    assert m["total_lock_extension_cost"] == 580
    assert m["total_lock_extension_days"] == 14
    assert m["loans_past_lock"] == 3
    assert m["avg_cycle_days"] == 25.2


def test_lock_extension_is_charged_per_started_day():
    loans = generate_portfolio(14, seed=42)
    schedule = fifo_schedule(loans, **STAFF)
    loan = loans[0]
    closing_row(schedule, loan.loan_id)["end"] = loan.lock_expiry + 1  # 1 hour late
    row = next(p for p in compute_metrics(schedule, loans)["per_loan"]
               if p["loan_id"] == loan.loan_id)
    assert row["lock_ext_days"] == 1
    assert row["lock_ext_cost"] == loan.lock_ext_cost_per_day


def test_validator_flags_a_late_loan_estimate():
    loans = generate_portfolio(14, seed=42)
    schedule = fifo_schedule(loans, **STAFF)
    problems = check_schedule(schedule, loans, **STAFF)
    assert sum("Loan Estimate late" in p for p in problems) == 12


def test_validator_flags_closing_inside_the_waiting_period():
    loans = generate_portfolio(14, seed=42)
    schedule = copy.deepcopy(fifo_schedule(loans, **STAFF))
    lid = loans[0].loan_id
    cd_end = next(r["end"] for r in schedule
                  if r["loan_id"] == lid and r["stage"] == "cd_prep")
    row = closing_row(schedule, lid)
    duration = row["end"] - row["start"]
    row["start"], row["end"] = cd_end, cd_end + duration
    problems = check_schedule(schedule, loans, **STAFF, enforce_le_deadline=False)
    assert any("waiting period" in p for p in problems)


def test_validator_flags_broken_precedence():
    loans = generate_portfolio(14, seed=42)
    schedule = copy.deepcopy(fifo_schedule(loans, **STAFF))
    lid = loans[0].loan_id
    row = next(r for r in schedule
               if r["loan_id"] == lid and r["stage"] == "final_uw")
    duration = row["end"] - row["start"]
    row["start"], row["end"] = loans[0].app_time, loans[0].app_time + duration
    problems = check_schedule(schedule, loans, **STAFF, enforce_le_deadline=False)
    assert any("starts before" in p for p in problems)


def test_validator_flags_a_double_booked_underwriter():
    loans = generate_portfolio(14, seed=42)
    schedule = copy.deepcopy(fifo_schedule(loans, **STAFF))
    uw_rows = [r for r in schedule
               if r["stage"] == "initial_uw" and r["resource"] == "UW-1"]
    first, second = uw_rows[0], uw_rows[1]
    duration = second["end"] - second["start"]
    second["start"], second["end"] = first["start"], first["start"] + duration
    problems = check_schedule(schedule, loans, **STAFF, enforce_le_deadline=False)
    assert any("overlap" in p for p in problems)


def test_validator_flags_an_overloaded_pool():
    loans = generate_portfolio(14, seed=42)
    schedule = fifo_schedule(loans, **STAFF)   # built with 3 processors
    problems = check_schedule(schedule, loans, n_processors=1,
                              n_underwriters=2, n_closers=2,
                              enforce_le_deadline=False)
    assert any(p.startswith("processor") for p in problems)
