"""
CP-SAT scheduling model for a TRID-constrained mortgage pipeline.

Decision: when each task of each loan runs, and which underwriter
handles each file.

Hard constraints
  1. Precedence DAG within each loan (job-shop structure).
  2. TRID Loan Estimate rule: LE delivered <= 3 business days after app.
  3. TRID waiting period: closing starts >= 3 business days after CD delivery.
  4. Processor / closer pool capacity (cumulative).
  5. Underwriters modeled as individual machines (optional intervals +
     NoOverlap) with file continuity: the SAME underwriter does initial
     and final underwriting for a given loan.
  6. No task starts before the loan's application time.

Soft constraints (objective)
  - Rate-lock extension cost: $/business-day for every day funding lands
    past lock expiry (the real money in mortgage ops).
  - Target-close tardiness penalty (borrower experience / contract risk).
  - Small earliness incentive to keep the pipeline moving.
"""

from ortools.sat.python import cp_model

from pipeline import (STAGES, STAGE_INDEX, PROCESSOR, UNDERWRITER, CLOSER,
                      EXTERNAL, HOURS_PER_DAY, LE_DEADLINE_HOURS,
                      CD_WAITING_HOURS)

TARDINESS_WEIGHT_PER_HOUR = 5   # $ proxy per business hour past target close
EARLINESS_WEIGHT = 1            # tiny pressure to finish files sooner


def solve_schedule(loans, n_processors=3, n_underwriters=2, n_closers=2,
                   horizon_days=120, time_limit_s=60, verbose=True):
    model = cp_model.CpModel()
    horizon = horizon_days * HOURS_PER_DAY

    # ---- task interval variables -----------------------------------------
    # tasks[(loan_id, stage_key)] = dict(start, end, interval, duration)
    tasks = {}
    for loan in loans:
        for stage in STAGES:
            dur = loan.durations[stage.key]
            suffix = f"{loan.loan_id}_{stage.key}"
            start = model.NewIntVar(loan.app_time, horizon, f"start_{suffix}")
            end = model.NewIntVar(loan.app_time, horizon, f"end_{suffix}")
            interval = model.NewIntervalVar(start, dur, end, f"iv_{suffix}")
            tasks[(loan.loan_id, stage.key)] = {
                "start": start, "end": end, "interval": interval, "dur": dur,
            }

    # ---- precedence within each loan --------------------------------------
    for loan in loans:
        for stage in STAGES:
            for pred in stage.predecessors:
                model.Add(tasks[(loan.loan_id, stage.key)]["start"]
                          >= tasks[(loan.loan_id, pred)]["end"])

    # ---- TRID hard constraints --------------------------------------------
    for loan in loans:
        # Loan Estimate out the door within 3 business days of application
        model.Add(tasks[(loan.loan_id, "le_prep")]["end"]
                  <= loan.app_time + LE_DEADLINE_HOURS)
        # 3-business-day waiting period between CD delivery and closing
        model.Add(tasks[(loan.loan_id, "closing_funding")]["start"]
                  >= tasks[(loan.loan_id, "cd_prep")]["end"]
                  + CD_WAITING_HOURS)

    # ---- pooled resources: processors & closers (cumulative) --------------
    for resource, capacity in ((PROCESSOR, n_processors), (CLOSER, n_closers)):
        intervals, demands = [], []
        for loan in loans:
            for stage in STAGES:
                if stage.resource == resource:
                    intervals.append(tasks[(loan.loan_id, stage.key)]["interval"])
                    demands.append(1)
        model.AddCumulative(intervals, demands, capacity)

    # ---- underwriters: individual machines + file continuity --------------
    uw_stage_keys = [s.key for s in STAGES if s.resource == UNDERWRITER]
    uw_assignment = {}   # (loan_id, uw_index) -> BoolVar  (continuity!)
    uw_intervals = {u: [] for u in range(n_underwriters)}

    for loan in loans:
        presence = []
        for u in range(n_underwriters):
            lit = model.NewBoolVar(f"uw_{loan.loan_id}_u{u}")
            uw_assignment[(loan.loan_id, u)] = lit
            presence.append(lit)
            for key in uw_stage_keys:
                t = tasks[(loan.loan_id, key)]
                opt = model.NewOptionalIntervalVar(
                    t["start"], t["dur"], t["end"], lit,
                    f"opt_{loan.loan_id}_{key}_u{u}")
                uw_intervals[u].append(opt)
        # each loan is assigned to exactly one underwriter, who does
        # BOTH its initial and final underwriting (continuity)
        model.AddExactlyOne(presence)

    for u in range(n_underwriters):
        model.AddNoOverlap(uw_intervals[u])

    # ---- objective ---------------------------------------------------------
    objective_terms = []
    lock_tardiness = {}
    for loan in loans:
        funded = tasks[(loan.loan_id, "closing_funding")]["end"]

        # rate-lock extension: hours past lock expiry, costed per business day
        late = model.NewIntVar(0, horizon, f"lock_late_{loan.loan_id}")
        model.AddMaxEquality(late, [funded - loan.lock_expiry, 0])
        lock_tardiness[loan.loan_id] = late
        cost_per_hour = max(1, loan.lock_ext_cost_per_day // HOURS_PER_DAY)
        objective_terms.append(late * cost_per_hour)

        # target-close tardiness
        tardy = model.NewIntVar(0, horizon, f"tardy_{loan.loan_id}")
        model.AddMaxEquality(tardy, [funded - loan.target_close, 0])
        objective_terms.append(tardy * TARDINESS_WEIGHT_PER_HOUR)

        # gentle earliness pressure
        objective_terms.append(funded * EARLINESS_WEIGHT)

    model.Minimize(sum(objective_terms))

    # ---- solve -------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"No feasible schedule found (status={solver.StatusName(status)}). "
                           "Try more staff or a longer horizon.")

    if verbose:
        print(f"Solver status : {solver.StatusName(status)}")
        print(f"Objective     : {solver.ObjectiveValue():,.0f}")
        print(f"Wall time     : {solver.WallTime():.1f}s")

    # ---- extract schedule --------------------------------------------------
    schedule = []
    for loan in loans:
        assigned_uw = next(u for u in range(n_underwriters)
                           if solver.Value(uw_assignment[(loan.loan_id, u)]))
        for stage in STAGES:
            t = tasks[(loan.loan_id, stage.key)]
            res = stage.resource
            label = f"UW-{assigned_uw + 1}" if res == UNDERWRITER else res
            schedule.append({
                "loan_id": loan.loan_id,
                "borrower": loan.borrower,
                "loan_type": loan.loan_type,
                "stage": stage.key,
                "stage_name": stage.name,
                "resource": label,
                "start": solver.Value(t["start"]),
                "end": solver.Value(t["end"]),
            })
    return schedule, solver
