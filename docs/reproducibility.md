# Reproducibility Guide

This repository is designed to be runnable with the Python standard library only.

## Environment

Recommended environment:

```bash
python --version
python -m pip install -r requirements.txt
```

`requirements.txt` intentionally contains no third-party runtime packages.

## Fast Verification

Run:

```bash
python scripts/smoke_test.py
```

The smoke test runs the deterministic baseline, the GA solver, and the GA + local-search solver on `instances/toy.json`. It validates that each output contains a schedule and a numeric score.

## Single-Instance Runs

Deterministic baseline:

```bash
python src/smart_tv_scheduler_scoreboost.py instances/toy.json results/toy_output.json
```

Hybrid GA:

```bash
python src/smart_tv_scheduler_ga2.py instances/toy.json results_ga/toy_ga_smoke.json --runs 1 --time-limit 5 --population 12 --elite 1 --top-k 8 --seed 42
```

Hybrid GA with local search:

```bash
python src/smart_tv_scheduler_ga2_with_local_search.py instances/toy.json results_ga_localsearch/toy_ls_smoke.json --runs 1 --time-limit 5 --population 12 --elite 1 --top-k 8 --seed 42 --local-search-max-seconds 2 --local-search-iterations 5
```

## Full Experiment Reruns

Deterministic baseline for all configured instances:

```bash
python scripts/run_all_instances.py
```

GA parameter tuning:

```bash
python scripts/run_all_instances_ga2.py
```

GA + local search with selected best parameters:

```bash
python scripts/run_best_params_local_search_batch.py
```

The full GA scripts can require substantial time. Before running them, inspect the script constants:

- `EXECUTIONS_PER_INSTANCE`
- `TIME_LIMIT`
- `TARGET_INSTANCES`
- `PARAMETER_CONFIGS`
- `BEST_PARAMS`

## Reference Results

The checked-in reference result summaries are:

- `tables/results_summary.csv`
- `tables/results_Final.csv`
- `tables/local_search_best_params_runs.csv`

The checked-in JSON schedules are stored under:

- `results/`
- `results_ga/`
- `results_ga_localsearch/`

## Randomness

The GA uses a base seed and derives run seeds deterministically. The batch scripts store the seed and parameter configuration in each output file or CSV row. Because some runs stop by elapsed time, independent reruns on different machines may not be byte-for-byte identical even when the same seeds are used.

## Validation

A result is considered valid when:

- the output JSON contains `scheduled_programs`;
- each scheduled item has `program_id`, `channel_id`, `start`, and `end`;
- `start < end` for every scheduled item;
- `total_score` is numeric;
- GA metadata reports `feasible: true`.
