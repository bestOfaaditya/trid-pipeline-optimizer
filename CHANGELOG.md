# Changelog

What changed in each version, file by file. Newest first.

## 0.4.0

Repository hygiene. No change to the model or its results.

- `src/validate.py` (new): checks a finished schedule against every rule independently of the scheduler that built it.
- `tests/` (new): generator, FIFO baseline, metrics and validator tests, plus CP-SAT tests that are skipped without OR-Tools.
- `.github/workflows/tests.yml` (new): runs the tests and one small end-to-end solve. Manual trigger for now.
- `.gitignore`: ignores `output/` and `data/` entirely. Before, only `output/*.png` and `output/*.csv` were ignored, and README charts had nowhere tracked to live.
- `requirements.txt`: upper bounds on OR-Tools and matplotlib. `requirements-dev.txt` adds pytest.
- `README.md`: results from two runs, tests, limitations.

## 0.3.0

Chart fixes after running with 5 underwriters.

- `src/visualize.py`: the colour map was hardcoded for UW-1 to UW-4, so a fifth underwriter was drawn in an unlabelled grey. Colours and legend are now built from the resources present in the schedule. Added markers for application time, the Loan Estimate deadline and late Loan Estimates, with the violation count in the title. Legend moved below the plot.
- `src/metrics.py`: removed the second, markdown copy of the comparison table from the console output.

## 0.2.0

Loan size enters the objective.

- `src/generate.py`: loans have a `principal` and a `bps_per_day`. The daily lock extension fee is `principal * bps / 10000` instead of a flat amount picked from a list.
- `src/pipeline.py`: pricing constants (0.75 to 2.0 bps per day) and objective weights in cents.
- `src/model.py`: lateness priced in integer cents per hour instead of dollars per hour, so loans with close but different fees stay distinguishable to the solver.
- `src/metrics.py`: reports loan value past lock and the average size of a loan past its lock next to the book average.
- `src/baseline.py`: unchanged. FIFO never reads cost, so loan size cannot affect it.

Results from 0.1.0 do not carry over. The generator draws more random numbers per loan, so the same seed gives a different portfolio, and total fees are about an order of magnitude lower than with the flat fee.

## 0.1.0

First working version.

- `src/pipeline.py`: 11-stage precedence graph per loan, resources, duration ranges, TRID constants.
- `src/generate.py`: seeded synthetic portfolio with a flat per-day lock extension fee.
- `src/baseline.py`: FIFO list scheduler.
- `src/model.py`: CP-SAT model with TRID deadlines as hard constraints, cumulative pools for processors and closers, and named underwriters with file continuity.
- `src/metrics.py`, `src/visualize.py`, `src/main.py`: comparison metrics, Gantt charts, command line runner.
