# Artifact Manifest

This file lists the main artifact components and their role in the PATAT 2026 submission repository.

## Source Code

- `src/smart_tv_scheduler_scoreboost.py`: deterministic dynamic-programming baseline.
- `src/smart_tv_scheduler_ga.py`: earlier GA implementation retained for traceability.
- `src/smart_tv_scheduler_ga2.py`: primary GA implementation used for parameter tuning.
- `src/smart_tv_scheduler_ga2_with_local_search.py`: GA implementation with local-search intensification.

## Inputs

- `instances/*.json`: benchmark instances. Each file defines the scheduling horizon, channels, programs, constraints, penalties, priority blocks, and time preferences.

## Outputs

- `results/*.json`: deterministic baseline schedules.
- `results_ga/*.json`: GA schedules from parameter tuning.
- `results_ga_localsearch/*.json`: schedules produced by GA + local search.

## Tables

- `tables/results_summary.csv`: deterministic score summary.
- `tables/results_Final.csv`: detailed GA parameter-tuning table.
- `tables/local_search_best_params_runs.csv`: detailed local-search table.

## Documentation

- `README.md`: artifact entry point.
- `docs/methodology.md`: method summary.
- `docs/algorithmic_notes.md`: deterministic baseline details.
- `docs/reproducibility.md`: commands for verification and reruns.
- `CITATION.cff`: machine-readable citation metadata.
- `LICENSE`: MIT License.
