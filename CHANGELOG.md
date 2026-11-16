# Changelog

What changed in each version, file by file. Newest first.

The dates are the days each version was written. The repository itself was put together on 2026-11-13, so the commits for 0.1.0 to 0.4.0 all carry that date.

## Which version touched which file

| File | 0.1.0 | 0.2.0 | 0.3.0 | 0.4.0 | 0.4.1 |
|---|---|---|---|---|---|
| `src/pipeline.py` | added | pricing constants, weights in cents | | | |
| `src/generate.py` | added | principal and bps per loan | | | |
| `src/baseline.py` | added | | | | |
| `src/model.py` | added | lateness in cents per hour | | | |
| `src/metrics.py` | added | loan value past lock | markdown table removed | | |
| `src/visualize.py` | added | | legend from data, TRID markers | | vendor entry in the CP-SAT legend |
| `src/main.py` | added | | | | |
| `src/validate.py` | | | | added | |
| `tests/`, `pytest.ini` | | | | added | |
| `.github/workflows/tests.yml` | | | | added | |
| `requirements.txt` | added | | | version bounds | |
| `requirements-dev.txt` | | | | added | |
| `.gitignore` | added | | | ignores `output/` and `data/` | |
| `README.md` | added | loan size section | | results, tests, limitations | results from a saved run, charts |
| `CHANGELOG.md` | | | | added | dates, this table |
| `docs/` | | | | | added |

`LICENSE` was added with the repository on 2026-08-04, before any of the code.

## 0.4.1 (2026-11-15)

Results re-run and charts added. No change to the model.

- `docs/` (new): Gantt charts for both runs in the README, plus the console output and CP-SAT schedule of each, so every number there can be traced to a file.
- `README.md`: the CP-SAT columns now come from that saved run, with the machine and package versions it ran on. The 14-loan charts are shown under the first table. The 30-loan CP-SAT figures changed slightly (the solve is time-limited), and the earlier figures are quoted next to them.
- `src/visualize.py`: the CP-SAT chart had no legend entry for vendor time. The CP-SAT schedule labels those tasks `external`, the FIFO one `vendor`, and the legend only looked for `vendor`. Both now show as vendor.
- `CHANGELOG.md`: dates for each version and the file table above.

## 0.4.0 (2026-11-13)

Repository hygiene. No change to the model or its results.

- `src/validate.py` (new): checks a finished schedule against every rule independently of the scheduler that built it.
- `tests/` (new): generator, FIFO baseline, metrics and validator tests, plus CP-SAT tests that are skipped without OR-Tools.
- `.github/workflows/tests.yml` (new): runs the tests and one small end-to-end solve. Manual trigger for now.
- `.gitignore`: ignores `output/` and `data/` entirely. Before, only `output/*.png` and `output/*.csv` were ignored, and README charts had nowhere tracked to live.
- `requirements.txt`: upper bounds on OR-Tools and matplotlib. `requirements-dev.txt` adds pytest.
- `README.md`: results from two runs, tests, limitations.

## 0.3.0 (2026-08-05)

Chart fixes after running with 5 underwriters.

- `src/visualize.py`: the colour map was hardcoded for UW-1 to UW-4, so a fifth underwriter was drawn in an unlabelled grey. Colours and legend are now built from the resources present in the schedule. Added markers for application time, the Loan Estimate deadline and late Loan Estimates, with the violation count in the title. Legend moved below the plot.
- `src/metrics.py`: removed the second, markdown copy of the comparison table from the console output.

## 0.2.0 (2026-08-04)

Loan size enters the objective.

- `src/generate.py`: loans have a `principal` and a `bps_per_day`. The daily lock extension fee is `principal * bps / 10000` instead of a flat amount picked from a list.
- `src/pipeline.py`: pricing constants (0.75 to 2.0 bps per day) and objective weights in cents.
- `src/model.py`: lateness priced in integer cents per hour instead of dollars per hour, so loans with close but different fees stay distinguishable to the solver.
- `src/metrics.py`: reports loan value past lock and the average size of a loan past its lock next to the book average.
- `src/baseline.py`: unchanged. FIFO never reads cost, so loan size cannot affect it.

Results from 0.1.0 do not carry over. The generator draws more random numbers per loan, so the same seed gives a different portfolio, and total fees are about an order of magnitude lower than with the flat fee.

## 0.1.0 (2026-06-10)

First working version.

- `src/pipeline.py`: 11-stage precedence graph per loan, resources, duration ranges, TRID constants.
- `src/generate.py`: seeded synthetic portfolio with a flat per-day lock extension fee.
- `src/baseline.py`: FIFO list scheduler.
- `src/model.py`: CP-SAT model with TRID deadlines as hard constraints, cumulative pools for processors and closers, and named underwriters with file continuity.
- `src/metrics.py`, `src/visualize.py`, `src/main.py`: comparison metrics, Gantt charts, command line runner.
