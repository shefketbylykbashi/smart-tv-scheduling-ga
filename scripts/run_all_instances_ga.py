import csv
import json
import os
import sys
import time
from pathlib import Path

# ------------------------------------------------------------
# Make src/ importable
# ------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from smart_tv_scheduler_ga2 import run_multi  # noqa: E402


# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
INSTANCES_DIR = REPO_ROOT / "instances"
RESULTS_GA_DIR = REPO_ROOT / "results_ga"
TABLES_DIR = REPO_ROOT / "tables"
SUMMARY_CSV = TABLES_DIR / "results_ga_summary2.csv"

RUNS = 3
TIME_LIMIT = 30
POPULATION = 24
ELITE = 2
TOP_K = 8
BASE_SEED = 42
ALLOW_PROGRAM_REVISIT = False
REVISIT_PENALTY = 25


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def ensure_directories():
    RESULTS_GA_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)


def list_instance_files():
    if not INSTANCES_DIR.exists():
        raise FileNotFoundError(f"Instances directory not found: {INSTANCES_DIR}")

    files = sorted([p for p in INSTANCES_DIR.glob("*.json") if p.is_file()])
    return files


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def format_seconds(x):
    return round(float(x), 4)


# ------------------------------------------------------------
# Main batch runner
# ------------------------------------------------------------
def main():
    ensure_directories()

    instance_files = list_instance_files()
    if not instance_files:
        print("No instance JSON files found in:", INSTANCES_DIR)
        return

    summary_rows = []
    total_start = time.time()

    print("=" * 90)
    print("Running GA on all instances")
    print(f"Instances dir : {INSTANCES_DIR}")
    print(f"Results dir   : {RESULTS_GA_DIR}")
    print(f"Summary CSV   : {SUMMARY_CSV}")
    print(f"Parameters    : runs={RUNS}, time_limit={TIME_LIMIT}, population={POPULATION}, elite={ELITE}, top_k={TOP_K}")
    print("=" * 90)

    for idx, instance_path in enumerate(instance_files, start=1):
        instance_name = instance_path.stem
        output_path = RESULTS_GA_DIR / f"{instance_name}_ga.json"

        print(f"[{idx}/{len(instance_files)}] Running: {instance_name}")

        try:
            data = load_json(instance_path)

            t0 = time.time()
            best_result, all_runs = run_multi(
                data=data,
                runs=RUNS,
                time_limit=TIME_LIMIT
            )
            elapsed = time.time() - t0

            save_json(output_path, best_result)

            meta = best_result.get("meta", {})
            experiment = best_result.get("experiment", {})

            best_score = best_result.get("total_score", 0)
            avg_score = experiment.get("average_score", 0)
            std_dev = experiment.get("std_dev", 0)
            switches = meta.get("switches", 0)
            partials = meta.get("partials", 0)
            bonus = meta.get("bonus", 0)
            program_score = meta.get("program_score", 0)
            feasible = meta.get("feasible", False)
            deterministic_seed_score = meta.get("deterministic_seed_score", 0)
            normalized_length = meta.get("normalized_length", 0)

            print(
                f"    score={best_score} | avg={avg_score} | std={std_dev} | "
                f"seed_score={deterministic_seed_score} | feasible={feasible} | "
                f"time={format_seconds(elapsed)}s"
            )

            summary_rows.append({
                "instance": instance_name,
                "best_score": best_score,
                "average_score": avg_score,
                "std_dev": std_dev,
                "deterministic_seed_score": deterministic_seed_score,
                "feasible": feasible,
                "switches": switches,
                "partials": partials,
                "bonus": bonus,
                "program_score": program_score,
                "normalized_length": normalized_length,
                "runs": RUNS,
                "time_limit_per_run_seconds": TIME_LIMIT,
                "population": POPULATION,
                "elite": ELITE,
                "top_k": TOP_K,
                "runtime_seconds_batch_call": format_seconds(elapsed),
                "output_file": str(output_path.relative_to(REPO_ROOT)),
            })

        except Exception as e:
            print(f"    ERROR on {instance_name}: {e}")

            summary_rows.append({
                "instance": instance_name,
                "best_score": "",
                "average_score": "",
                "std_dev": "",
                "deterministic_seed_score": "",
                "feasible": False,
                "switches": "",
                "partials": "",
                "bonus": "",
                "program_score": "",
                "normalized_length": "",
                "runs": RUNS,
                "time_limit_per_run_seconds": TIME_LIMIT,
                "population": POPULATION,
                "elite": ELITE,
                "top_k": TOP_K,
                "runtime_seconds_batch_call": "",
                "output_file": "",
                "error": str(e),
            })

    # Write CSV summary
    fieldnames = [
        "instance",
        "best_score",
        "average_score",
        "std_dev",
        "deterministic_seed_score",
        "feasible",
        "switches",
        "partials",
        "bonus",
        "program_score",
        "normalized_length",
        "runs",
        "time_limit_per_run_seconds",
        "population",
        "elite",
        "top_k",
        "runtime_seconds_batch_call",
        "output_file",
        "error",
    ]

    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            if "error" not in row:
                row["error"] = ""
            writer.writerow(row)

    total_elapsed = time.time() - total_start

    print("=" * 90)
    print("Finished GA batch run")
    print(f"Instances processed : {len(instance_files)}")
    print(f"Results saved in    : {RESULTS_GA_DIR}")
    print(f"Summary saved in    : {SUMMARY_CSV}")
    print(f"Total elapsed time  : {format_seconds(total_elapsed)}s")
    print("=" * 90)


if __name__ == "__main__":
    main()