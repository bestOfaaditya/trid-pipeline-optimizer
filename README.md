# TRID-Aware Mortgage Pipeline Scheduler

[![tests](https://github.com/bestOfaaditya/trid-pipeline-optimizer/actions/workflows/tests.yml/badge.svg)](https://github.com/bestOfaaditya/trid-pipeline-optimizer/actions/workflows/tests.yml)

A constraint programming (CP-SAT) scheduler for a mortgage lender's in-flight loans. TRID disclosure deadlines are hard constraints and rate-lock extension fees are the cost being minimized. A FIFO scheduler is included as the baseline to compare against.

## The problem

A lender has many loans in process at once and a small team of processors, underwriters and closers. Every loan goes through the same steps and competes for the same people. Two timing rules from TRID ([12 CFR 1026.19](https://www.consumerfinance.gov/rules-policy/regulations/1026/2023-01-01/19/)) apply to every loan:

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

### Loan size

Lock extensions are priced as basis points of the loan amount per day (0.75 to 2.0 bps), not as a flat fee. A 900k loan costs about 3x what a 300k loan costs for each late day at the same rate, so when there is not enough capacity the solver lets the small loans slip first. FIFO never looks at cost, so loan size has no effect on it. The metric that shows this is the average size of the loans that went past their lock, compared with the average loan in the book.

The bps range is an assumption taken from published lender guidance: 2 to 3 bps per day ([Modern Home Lending](https://www.modernhomelending.com/all-blogs/rate-lock-explained)), 0.01% to 0.03% of the loan per day ([Oasis Home Mortgages](https://www.oasishomemortgages.com/mortgage-rate-lock-30-60-90-day-protection-strategies/)), and 10 to 12 bps for a 15-day extension, which is under 1 bp per day ([Fellowship Home Loans](https://fellowshiphomeloans.com/what-if-your-rate-lock-expires-before-closing/)). Some lenders charge a flat fee instead.

## Results

Both runs use seed 42. The FIFO column is deterministic and is pinned by a test. The CP-SAT column comes from a time-limited solve on my laptop, so it can move a little on another machine.

### Enough staff: 14 loans, 3 processors, 2 underwriters, 2 closers

```bash
python src/main.py
```

| Metric | FIFO | CP-SAT |
|---|---|---|
| Loan Estimate deadline misses | 12 | 0 |
| Rate-lock extension cost | $580 | $0 |
| Lock extension days | 14 | 0 |
| Loans past their lock | 3 | 0 |
| Loans past target close | 2 | 0 |
| Avg cycle time (business days) | 25.2 | 14.6 |

### Not enough staff: 30 loans, 1 underwriter

```bash
python src/main.py --loans 30 --underwriters 1 --time-limit 120
```

| Metric | FIFO | CP-SAT |
|---|---|---|
| Loan Estimate deadline misses | 28 | 0 |
| Rate-lock extension cost | $57,379 | $1,883 |
| Lock extension days | 853 | 64 |
| Loans past their lock | 22 | 7 |
| Loans past target close | 21 | 5 |
| Avg cycle time (business days) | 60.1 | 29.8 |
| Loan value past lock | $11,595,000 | $2,095,000 |
| Avg size of a loan past its lock | $527,045 | $299,286 |

### How to read these

The Loan Estimate row is a different kind of number from the rest. It is a legal deadline, and in the model it is a hard constraint, so the solver cannot return a schedule that misses it. The zero is there by construction. FIFO misses it on most loans because it does not start a file until the ones ahead of it are done, and by then the 3 days are gone.

The other rows are costs. With one underwriter for 30 loans there is no schedule that funds everything on time, and CP-SAT still pays $1,883. What changes is which loans it lets slip. The average loan in that book is $521,000. The loans FIFO runs past their lock average $527,045, about the same as the book, because FIFO does not look at size. The ones CP-SAT lets slip average $299,286.

Most of the cycle time gain comes from ordering. CP-SAT gets the short tasks that start a long vendor wait (ordering the appraisal, sending the Loan Estimate) out early, and FIFO leaves them queued behind document collection for older files.

## Run it

```bash
pip install -r requirements.txt
python src/main.py                                # 14 loans, 3 processors, 2 underwriters, 2 closers
python src/main.py --loans 25 --underwriters 3
python src/main.py --no-solve                     # FIFO baseline only, OR-Tools not needed
python src/main.py --help
```

Charts and the optimized schedule CSV are written to `output/`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

`src/validate.py` re-checks a finished schedule against every rule without using the scheduler that produced it. The tests run it on FIFO and CP-SAT schedules and on a few schedules broken on purpose. The CP-SAT tests are skipped if OR-Tools is not installed.

## Layout

```
src/pipeline.py    stages, precedence graph, TRID and pricing constants
src/generate.py    synthetic loan portfolio (seeded)
src/baseline.py    FIFO scheduler
src/model.py       CP-SAT model
src/metrics.py     cost and compliance metrics
src/validate.py    independent schedule checker
src/visualize.py   Gantt charts
src/main.py        CLI
tests/             pytest suite
```

## Limitations

- The data is synthetic. Durations, lock lengths and fees are reasonable guesses, not a lender's numbers.
- Durations are fixed and known in advance. Real appraisal and title turn times vary, and a lot of real delay is waiting on the borrower.
- It solves one snapshot. A real pipeline gets new applications every day and would need re-solving on a rolling basis.
- The clock is a flat 8-hour business day. TRID has its own day-counting rules (which days count differs between the two deadlines) and those are not modelled.
- No rework loops: a file never bounces back from underwriting, and a changed circumstance never forces a new Loan Estimate.
- Every loan is assumed to fund. No fallout or denials.
- The cost side is lock fees plus a tardiness proxy. Labour cost and the value of the loan beyond its fee are left out.

See [CHANGELOG.md](CHANGELOG.md) for how the model changed between versions.

## How this was built

I have an MS in Operations Research from Stony Brook and spent three years at Deloitte on payment validation for US banking clients. The code here was written with AI assistance (Claude). The choices on pricing and weighting, the experiment runs and the checking of results are mine.

## License

MIT
