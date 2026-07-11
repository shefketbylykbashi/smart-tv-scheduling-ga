# Smart TV Scheduling GA Artifact

Research artifact for a Smart TV Scheduling optimization approach prepared for PATAT 2026 submission 8479.

Author and maintainer: **Shefket Bylykbashi**

The repository contains the source code, benchmark instances, generated schedules, result tables, and manuscript file for a hybrid scheduling method that combines a deterministic dynamic-programming seed with a Genetic Algorithm and an optional local-search intensification phase.

## Repository Contents

| Path | Purpose |
| --- | --- |
| `src/smart_tv_scheduler_scoreboost.py` | Deterministic baseline and seed generator. |
| `src/smart_tv_scheduler_ga2.py` | Hybrid Genetic Algorithm scheduler. |
| `src/smart_tv_scheduler_ga2_with_local_search.py` | Hybrid GA with local-search intensification. |
| `instances/` | JSON benchmark instances used in the experiments. |
| `results/` | Deterministic baseline outputs. |
| `results_ga/` | GA parameter-tuning outputs. |
| `results_ga_localsearch/` | GA + local-search outputs. |
| `tables/` | CSV summaries used for reporting and comparison. |
| `scripts/` | Batch runners, recovery utilities, and smoke test. |
| `docs/` | Method, artifact, and reproducibility notes. |
| `PATAT 2026_submission_8479_paper_v3.pdf` | Submitted PATAT 2026 manuscript file. |

## Problem Summary

The Smart TV Scheduling problem constructs a broadcast schedule for a single screen in a public venue by selecting compatible program segments from multiple TV channels. The objective maximizes total utility while respecting temporal feasibility, priority-block channel restrictions, minimum broadcast duration, and limits on consecutive programs with the same genre. The score combines program value and preference bonuses, then subtracts penalties for channel switching and partial broadcasts.

## Method

The implementation follows this high-level pipeline:

1. Build feasible candidate segments from channel programs.
2. Score segments using program score, time-preference bonuses, and truncation penalties.
3. Keep the top `K` candidate segments per program.
4. Generate a deterministic schedule with dynamic programming.
5. Use the deterministic schedule as a seed for the Genetic Algorithm.
6. Improve schedules through selection, crossover, mutation, repair, and elitism.
7. Optionally intensify the best GA solution with local search.

See [docs/methodology.md](docs/methodology.md) and [docs/algorithmic_notes.md](docs/algorithmic_notes.md) for the detailed algorithmic description.

## Requirements

- Python 3.10 or newer
- No external Python packages are required

The artifact was checked locally with Python 3.13.0.

## Quick Start

Run the smoke test first:

```bash
python scripts/smoke_test.py
```

Run the deterministic baseline on the toy instance:

```bash
python src/smart_tv_scheduler_scoreboost.py instances/toy.json results/toy_output.json
```

Run one short GA execution:

```bash
python src/smart_tv_scheduler_ga2.py instances/toy.json results_ga/toy_ga_smoke.json --runs 1 --time-limit 5 --population 12 --elite 1 --top-k 8 --seed 42
```

Run one short GA + local-search execution:

```bash
python src/smart_tv_scheduler_ga2_with_local_search.py instances/toy.json results_ga_localsearch/toy_ls_smoke.json --runs 1 --time-limit 5 --population 12 --elite 1 --top-k 8 --seed 42 --local-search-max-seconds 2 --local-search-iterations 5
```

## Reproducing the Experiments

The checked-in CSV files and JSON outputs are the reference results for the submitted artifact. Full reruns can take a long time because the GA experiments use multiple instances, configurations, and random seeds.

```bash
python scripts/run_all_instances.py
python scripts/run_all_instances_ga2.py
python scripts/run_best_params_local_search_batch.py
```

Before launching a long rerun, inspect the constants at the top of each batch script, especially `TIME_LIMIT`, `EXECUTIONS_PER_INSTANCE`, `TARGET_INSTANCES`, and the parameter configuration lists.

Detailed reproduction instructions are in [docs/reproducibility.md](docs/reproducibility.md).

## Results Files

The main result summaries are:

- `tables/results_summary.csv`: deterministic baseline scores.
- `tables/results_Final.csv`: GA parameter-tuning results.
- `tables/local_search_best_params_runs.csv`: GA + local-search runs.

The complete per-instance schedules are stored as JSON files under `results/`, `results_ga/`, and `results_ga_localsearch/`.

## Output Format

Solver output JSON files contain:

```json
{
  "scheduled_programs": [
    {
      "program_id": "example",
      "channel_id": "channel",
      "start": 0,
      "end": 30
    }
  ],
  "total_score": 0,
  "meta": {}
}
```

The deterministic baseline omits `meta`; GA-based outputs include run parameters, feasibility status, score components, runtime, seed, and local-search statistics when applicable.

## Citation

If you use this repository, cite the artifact using [CITATION.cff](CITATION.cff). A human-readable form is:

> Shefket Bylykbashi. Smart TV Scheduling Genetic Algorithm Artifact. PATAT 2026 submission 8479 artifact, version 1.0.0, 2026.

## License

This repository is released under the MIT License. See [LICENSE](LICENSE).
