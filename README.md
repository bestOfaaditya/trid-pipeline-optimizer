# TRID-Aware Mortgage Pipeline Scheduler

A constraint programming (CP-SAT) scheduler for a mortgage lender's in-flight loans. TRID disclosure deadlines are hard constraints and rate-lock extension fees are the cost being minimized. A FIFO scheduler is included as the baseline to compare against.

## The problem

A lender has many loans in process at once and a small team of processors, underwriters and closers. Every loan goes through the same steps and competes for the same people. Two timing rules from TRID (12 CFR 1026.19) apply to every loan:

- the Loan Estimate has to go out within 3 business days of the application
- the borrower has to receive the Closing Disclosure at least 3 business days before closing

Each loan also has a rate lock. If the loan funds after the lock expires, someone pays an extension fee for every day it is late.

Working files in application order (FIFO) ignores all of this. This project treats the pipeline as a job-shop scheduling problem instead.

## Pipeline

Each loan is 11 tasks in a precedence graph. Three branches run in parallel and meet at final underwriting.

```
intake -> LE prep --+-- doc collection -> initial UW -> conditions --+
                    +-- order appraisal -> appraisal (vendor) -------+-> final UW -> CD prep -> (3 day wait) -> closing
                    +-- title search (vendor) -----------------------+
```

## Model

| Element | CP-SAT construct |
|---|---|
| Each task of each loan | `NewIntervalVar` |
| Precedence | `start[succ] >= end[pred]` |
| Loan Estimate deadline | `end[le_prep] <= app_time + 24h` (hard) |
| Closing Disclosure wait | `start[closing] >= end[cd_prep] + 24h` (hard) |
| Processor and closer pools | `AddCumulative` |
| Underwriters | `NewOptionalIntervalVar` + `AddExactlyOne` + `AddNoOverlap`, same underwriter for both reviews of a loan |
| Lock extension | `AddMaxEquality(late, [funded - lock_expiry, 0])` |
| Objective | minimize lock extension cost + target-close tardiness + a small earliness term |

Time unit is one business hour, 8 hours to a business day.

## Run it

```bash
pip install -r requirements.txt
python src/main.py                                # 14 loans, 3 processors, 2 underwriters, 2 closers
python src/main.py --loans 25 --underwriters 3
python src/main.py --no-solve                     # FIFO baseline only, OR-Tools not needed
python src/main.py --help
```

Charts and the optimized schedule CSV are written to `output/`.
