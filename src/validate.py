"""
Independent schedule checker.

Takes any schedule (FIFO or CP-SAT) and re-checks every rule from scratch,
without trusting the code that produced it. Returns a list of readable
problems. An empty list means the schedule is valid.

The Loan Estimate deadline check is optional because the FIFO baseline is
allowed to miss it (that is what the comparison measures). Every other
rule is physical and has to hold for both schedulers.
"""

from pipeline import (STAGES, PROCESSOR, UNDERWRITER, CLOSER,
                      LE_DEADLINE_HOURS, CD_WAITING_HOURS)


def _peak_concurrency(intervals):
    """Largest number of intervals running at the same instant."""
    events = []
    for start, end in intervals:
        events.append((start, 1))
        events.append((end, -1))
    # at equal times, process ends before starts: back-to-back is not overlap
    events.sort(key=lambda e: (e[0], e[1]))
    peak = running = 0
    for _, delta in events:
        running += delta
        peak = max(peak, running)
    return peak


def check_schedule(schedule, loans, n_processors, n_underwriters, n_closers,
                   enforce_le_deadline=True):
    problems = []

    rows = {}
    for r in schedule:
        key = (r["loan_id"], r["stage"])
        if key in rows:
            problems.append(f"{r['loan_id']}.{r['stage']}: scheduled more than once")
        rows[key] = r
    for loan in loans:
        for stage in STAGES:
            if (loan.loan_id, stage.key) not in rows:
                problems.append(f"{loan.loan_id}.{stage.key}: not scheduled")
    if problems:
        return problems   # the remaining checks need a complete schedule

    uw_keys = [s.key for s in STAGES if s.resource == UNDERWRITER]
    uw_intervals = {}     # underwriter label -> [(start, end, task name)]

    for loan in loans:
        lid = loan.loan_id
        for stage in STAGES:
            r = rows[(lid, stage.key)]
            name = f"{lid}.{stage.key}"
            if r["end"] - r["start"] != loan.durations[stage.key]:
                problems.append(f"{name}: duration {r['end'] - r['start']}h, "
                                f"expected {loan.durations[stage.key]}h")
            if r["start"] < loan.app_time:
                problems.append(f"{name}: starts before the application")
            for pred in stage.predecessors:
                if r["start"] < rows[(lid, pred)]["end"]:
                    problems.append(f"{name}: starts before {pred} ends")

        cd_end = rows[(lid, "cd_prep")]["end"]
        if rows[(lid, "closing_funding")]["start"] < cd_end + CD_WAITING_HOURS:
            problems.append(f"{lid}: closing inside the Closing Disclosure "
                            f"waiting period")

        if enforce_le_deadline:
            le_end = rows[(lid, "le_prep")]["end"]
            if le_end > loan.app_time + LE_DEADLINE_HOURS:
                problems.append(f"{lid}: Loan Estimate late by "
                                f"{le_end - loan.app_time - LE_DEADLINE_HOURS}h")

        labels = {rows[(lid, k)]["resource"] for k in uw_keys}
        if len(labels) != 1:
            problems.append(f"{lid}: underwriting split across {sorted(labels)}")
        for k in uw_keys:
            r = rows[(lid, k)]
            uw_intervals.setdefault(r["resource"], []).append(
                (r["start"], r["end"], f"{lid}.{k}"))

    # pooled staff: never more tasks running than people in the pool
    for resource, capacity in ((PROCESSOR, n_processors), (CLOSER, n_closers)):
        keys = [s.key for s in STAGES if s.resource == resource]
        spans = [(rows[(l.loan_id, k)]["start"], rows[(l.loan_id, k)]["end"])
                 for l in loans for k in keys]
        peak = _peak_concurrency(spans)
        if peak > capacity:
            problems.append(f"{resource}: {peak} tasks at once, "
                            f"capacity is {capacity}")

    # underwriters: named individuals, one file at a time
    if len(uw_intervals) > n_underwriters:
        problems.append(f"underwriter: {len(uw_intervals)} people used, "
                        f"only {n_underwriters} exist")
    for label, spans in uw_intervals.items():
        spans.sort()
        for (s1, e1, n1), (s2, e2, n2) in zip(spans, spans[1:]):
            if s2 < e1:
                problems.append(f"{label}: overlap between {n1} and {n2}")

    return problems
