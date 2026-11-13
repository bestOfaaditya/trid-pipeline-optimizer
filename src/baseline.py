"""
Baseline: FIFO greedy list scheduler.

This mimics how most lender back-offices actually run: files are worked
in application-date order, each task grabs the first free person, nobody
looks at lock expiry dates or the global picture. The TRID waiting period
is still respected (it's federal law), but the LE 3-day deadline can be
*missed* under load -- which is itself a finding: the optimizer treats it
as a hard constraint, FIFO just hopes.
"""

from pipeline import (STAGES, PROCESSOR, UNDERWRITER, CLOSER, EXTERNAL,
                      CD_WAITING_HOURS)


def fifo_schedule(loans, n_processors=3, n_underwriters=2, n_closers=2):
    # each pool = list of next-free times, one per person
    pools = {
        PROCESSOR: [0] * n_processors,
        CLOSER: [0] * n_closers,
    }
    uw_free = [0] * n_underwriters
    uw_of_loan = {}

    end_times = {}   # (loan_id, stage_key) -> end
    schedule = []

    # global FIFO: loans by application time; stages already topological
    for loan in sorted(loans, key=lambda l: l.app_time):
        for stage in STAGES:
            ready = loan.app_time
            for pred in stage.predecessors:
                ready = max(ready, end_times[(loan.loan_id, pred)])
            if stage.key == "closing_funding":
                ready = max(ready,
                            end_times[(loan.loan_id, "cd_prep")]
                            + CD_WAITING_HOURS)

            dur = loan.durations[stage.key]

            if stage.resource == EXTERNAL:
                start = ready
                label = "vendor"
            elif stage.resource == UNDERWRITER:
                # continuity: same UW for both underwriting touches
                if loan.loan_id not in uw_of_loan:
                    uw_of_loan[loan.loan_id] = min(
                        range(n_underwriters), key=lambda u: uw_free[u])
                u = uw_of_loan[loan.loan_id]
                start = max(ready, uw_free[u])
                uw_free[u] = start + dur
                label = f"UW-{u + 1}"
            else:
                pool = pools[stage.resource]
                idx = min(range(len(pool)), key=lambda i: pool[i])
                start = max(ready, pool[idx])
                pool[idx] = start + dur
                label = stage.resource

            end = start + dur
            end_times[(loan.loan_id, stage.key)] = end
            schedule.append({
                "loan_id": loan.loan_id,
                "borrower": loan.borrower,
                "loan_type": loan.loan_type,
                "stage": stage.key,
                "stage_name": stage.name,
                "resource": label,
                "start": start,
                "end": end,
            })
    return schedule
