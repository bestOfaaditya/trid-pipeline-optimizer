# Saved run output

Output of the two runs quoted in the main README, kept so the numbers there can be checked against a file.

| | |
|---|---|
| Date | 2026-11-15 |
| Code | 0.4.0 (the model is unchanged in 0.4.1) |
| Machine | Windows 11 laptop, 16 logical cores |
| Python | 3.11.9 |
| OR-Tools | 9.15.6755 |
| matplotlib | 3.11.2 |
| Tests on the same machine | 16 passed, including the 3 CP-SAT tests |

| File | What it is |
|---|---|
| `14_loans_console.txt` | console output of `python src/main.py` |
| `14_loans_schedule_cpsat.csv` | the CP-SAT schedule from that run |
| `30_loans_console.txt` | console output of `python src/main.py --loans 30 --underwriters 1 --time-limit 120` |
| `30_loans_schedule_cpsat.csv` | the CP-SAT schedule from that run |

Both solves ended at the time limit with status FEASIBLE, meaning the solver returned the best schedule it had found and did not prove it optimal. A rerun can land on a slightly different schedule. The FIFO side is deterministic and is the same on every run.

Both schedules pass `src/validate.py` with no problems. The portfolios are not saved here because `generate_portfolio(n, seed=42)` rebuilds them exactly.

The CP-SAT charts in `docs/` are drawn from these schedules. The FIFO charts are drawn from the FIFO schedule for the same portfolios.
