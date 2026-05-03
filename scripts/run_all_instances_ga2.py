import csv
import json
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

from smart_tv_scheduler_ga2 import run_one_ga  # noqa: E402


# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
INSTANCES_DIR = REPO_ROOT / "instances"
RESULTS_GA_DIR = REPO_ROOT / "results_ga"
TABLES_DIR = REPO_ROOT / "tables"

DETAILED_CSV = TABLES_DIR / "results_ga_parameter_tuning_detailed.csv"
SUMMARY_CSV = TABLES_DIR / "results_ga_parameter_tuning_summary.csv"

EXECUTIONS_PER_INSTANCE = 10
TIME_LIMIT = 300
BASE_SEED = 42

ALLOW_PROGRAM_REVISIT = False
REVISIT_PENALTY = 25


# ------------------------------------------------------------
# Parameter tuning configurations
# ------------------------------------------------------------
# Each execution uses one configuration from this list.
# You can modify these values depending on your experiment design.
PARAMETER_CONFIGS = [
    {
        "config_id": "C01",
        "top_k": 8,
        "population_size": 24,
        "elite_count": 2,
    },
    {
        "config_id": "C02",
        "top_k": 10,
        "population_size": 24,
        "elite_count": 2,
    },
    {
        "config_id": "C03",
        "top_k": 12,
        "population_size": 24,
        "elite_count": 2,
    },
    {
        "config_id": "C04",
        "top_k": 8,
        "population_size": 32,
        "elite_count": 2,
    },
    {
        "config_id": "C05",
        "top_k": 10,
        "population_size": 32,
        "elite_count": 2,
    },
    {
        "config_id": "C06",
        "top_k": 12,
        "population_size": 32,
        "elite_count": 2,
    },
    {
        "config_id": "C07",
        "top_k": 8,
        "population_size": 40,
        "elite_count": 3,
    },
    {
        "config_id": "C08",
        "top_k": 10,
        "population_size": 40,
        "elite_count": 3,
    },
    {
        "config_id": "C09",
        "top_k": 12,
        "population_size": 40,
        "elite_count": 3,
    },
    {
        "config_id": "C10",
        "top_k": 15,
        "population_size": 40,
        "elite_count": 3,
    },
]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def ensure_directories():
    RESULTS_GA_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)


def list_instance_files():
    if not INSTANCES_DIR.exists():
        raise FileNotFoundError(f"Instances directory not found: {INSTANCES_DIR}")

    return sorted([p for p in INSTANCES_DIR.glob("*.json") if p.is_file()])


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def format_seconds(x):
    return round(float(x), 4)


def safe_get(dictionary, key, default=""):
    if dictionary is None:
        return default
    return dictionary.get(key, default)


# ------------------------------------------------------------
# Main batch runner with parameter tuning
# ------------------------------------------------------------
def main():
    ensure_directories()

    instance_files = list_instance_files()
    if not instance_files:
        print("No instance JSON files found in:", INSTANCES_DIR)
        return

    detailed_rows = []
    summary_rows = []

    total_start = time.time()

    print("=" * 100)
    print("Running GA parameter tuning on all instances")
    print(f"Instances dir              : {INSTANCES_DIR}")
    print(f"Results dir                : {RESULTS_GA_DIR}")
    print(f"Detailed CSV               : {DETAILED_CSV}")
    print(f"Summary CSV                : {SUMMARY_CSV}")
    print(f"Executions per instance    : {EXECUTIONS_PER_INSTANCE}")
    print(f"Time limit per execution   : {TIME_LIMIT} seconds")
    print(f"Parameter configurations   : {len(PARAMETER_CONFIGS)}")
    print("=" * 100)

    for instance_idx, instance_path in enumerate(instance_files, start=1):
        instance_name = instance_path.stem

        print(f"\n[{instance_idx}/{len(instance_files)}] Instance: {instance_name}")

        best_result_for_instance = None
        best_score_for_instance = -10**18
        best_output_file = ""

        try:
            data = load_json(instance_path)
        except Exception as e:
            print(f"    ERROR loading instance {instance_name}: {e}")

            summary_rows.append({
                "instance": instance_name,
                "best_score": "",
                "best_execution": "",
                "best_config_id": "",
                "best_top_k": "",
                "best_population_size": "",
                "best_elite_count": "",
                "best_seed": "",
                "best_output_file": "",
                "error": str(e),
            })
            continue

        for execution_idx in range(1, EXECUTIONS_PER_INSTANCE + 1):
            config = PARAMETER_CONFIGS[(execution_idx - 1) % len(PARAMETER_CONFIGS)]

            config_id = config["config_id"]
            top_k = config["top_k"]
            population_size = config["population_size"]
            elite_count = config["elite_count"]

            seed = BASE_SEED + 1009 * execution_idx

            output_path = RESULTS_GA_DIR / (
                f"{instance_name}_ga_exec_{execution_idx:02d}_{config_id}.json"
            )

            print(
                f"    Execution {execution_idx:02d}/{EXECUTIONS_PER_INSTANCE} | "
                f"config={config_id} | top_k={top_k} | "
                f"population={population_size} | elite={elite_count} | seed={seed}"
            )

            execution_start = time.time()

            try:
                result = run_one_ga(
                    data=data,
                    top_k=top_k,
                    population_size=population_size,
                    elite_count=elite_count,
                    time_limit=TIME_LIMIT,
                    seed=seed,
                    allow_program_revisit=ALLOW_PROGRAM_REVISIT,
                    revisit_penalty=REVISIT_PENALTY,
                )

                runtime = time.time() - execution_start

                # Add explicit experiment information into the JSON output
                result["parameter_tuning"] = {
                    "instance": instance_name,
                    "execution": execution_idx,
                    "config_id": config_id,
                    "top_k": top_k,
                    "population_size": population_size,
                    "elite_count": elite_count,
                    "seed": seed,
                    "time_limit_seconds": TIME_LIMIT,
                    "allow_program_revisit": ALLOW_PROGRAM_REVISIT,
                    "revisit_penalty": REVISIT_PENALTY,
                    "runtime_seconds": format_seconds(runtime),
                }

                save_json(output_path, result)

                meta = result.get("meta", {})
                total_score = result.get("total_score", 0)

                row = {
                    "instance": instance_name,
                    "execution": execution_idx,
                    "config_id": config_id,
                    "score": total_score,
                    "feasible": safe_get(meta, "feasible", False),
                    "deterministic_seed_score": safe_get(meta, "deterministic_seed_score", ""),
                    "ga_score": safe_get(meta, "ga_score", total_score),
                    "switches": safe_get(meta, "switches", ""),
                    "partials": safe_get(meta, "partials", ""),
                    "bonus": safe_get(meta, "bonus", ""),
                    "program_score": safe_get(meta, "program_score", ""),
                    "revisits": safe_get(meta, "revisits", ""),
                    "normalized_length": safe_get(meta, "normalized_length", ""),
                    "top_k": top_k,
                    "population_size": population_size,
                    "elite_count": elite_count,
                    "seed": seed,
                    "time_limit_seconds": TIME_LIMIT,
                    "allow_program_revisit": ALLOW_PROGRAM_REVISIT,
                    "revisit_penalty": REVISIT_PENALTY,
                    "runtime_seconds": format_seconds(runtime),
                    "output_file": str(output_path.relative_to(REPO_ROOT)),
                    "error": "",
                }

                detailed_rows.append(row)

                print(
                    f"        score={total_score} | "
                    f"seed_score={row['deterministic_seed_score']} | "
                    f"feasible={row['feasible']} | "
                    f"time={row['runtime_seconds']}s"
                )

                if total_score > best_score_for_instance:
                    best_score_for_instance = total_score
                    best_result_for_instance = row
                    best_output_file = str(output_path.relative_to(REPO_ROOT))

            except Exception as e:
                runtime = time.time() - execution_start

                print(f"        ERROR: {e}")

                detailed_rows.append({
                    "instance": instance_name,
                    "execution": execution_idx,
                    "config_id": config_id,
                    "score": "",
                    "feasible": False,
                    "deterministic_seed_score": "",
                    "ga_score": "",
                    "switches": "",
                    "partials": "",
                    "bonus": "",
                    "program_score": "",
                    "revisits": "",
                    "normalized_length": "",
                    "top_k": top_k,
                    "population_size": population_size,
                    "elite_count": elite_count,
                    "seed": seed,
                    "time_limit_seconds": TIME_LIMIT,
                    "allow_program_revisit": ALLOW_PROGRAM_REVISIT,
                    "revisit_penalty": REVISIT_PENALTY,
                    "runtime_seconds": format_seconds(runtime),
                    "output_file": "",
                    "error": str(e),
                })

        if best_result_for_instance is not None:
            summary_rows.append({
                "instance": instance_name,
                "best_score": best_score_for_instance,
                "best_execution": best_result_for_instance["execution"],
                "best_config_id": best_result_for_instance["config_id"],
                "best_top_k": best_result_for_instance["top_k"],
                "best_population_size": best_result_for_instance["population_size"],
                "best_elite_count": best_result_for_instance["elite_count"],
                "best_seed": best_result_for_instance["seed"],
                "best_output_file": best_output_file,
                "error": "",
            })
        else:
            summary_rows.append({
                "instance": instance_name,
                "best_score": "",
                "best_execution": "",
                "best_config_id": "",
                "best_top_k": "",
                "best_population_size": "",
                "best_elite_count": "",
                "best_seed": "",
                "best_output_file": "",
                "error": "No successful execution",
            })

    # ------------------------------------------------------------
    # Write detailed CSV
    # ------------------------------------------------------------
    detailed_fieldnames = [
        "instance",
        "execution",
        "config_id",
        "score",
        "feasible",
        "deterministic_seed_score",
        "ga_score",
        "switches",
        "partials",
        "bonus",
        "program_score",
        "revisits",
        "normalized_length",
        "top_k",
        "population_size",
        "elite_count",
        "seed",
        "time_limit_seconds",
        "allow_program_revisit",
        "revisit_penalty",
        "runtime_seconds",
        "output_file",
        "error",
    ]

    with open(DETAILED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=detailed_fieldnames)
        writer.writeheader()
        writer.writerows(detailed_rows)

    # ------------------------------------------------------------
    # Write summary CSV
    # ------------------------------------------------------------
    summary_fieldnames = [
        "instance",
        "best_score",
        "best_execution",
        "best_config_id",
        "best_top_k",
        "best_population_size",
        "best_elite_count",
        "best_seed",
        "best_output_file",
        "error",
    ]

    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    total_elapsed = time.time() - total_start

    print("\n" + "=" * 100)
    print("Finished GA parameter tuning batch run")
    print(f"Instances processed       : {len(instance_files)}")
    print(f"Executions per instance   : {EXECUTIONS_PER_INSTANCE}")
    print(f"Results saved in          : {RESULTS_GA_DIR}")
    print(f"Detailed CSV saved in     : {DETAILED_CSV}")
    print(f"Summary CSV saved in      : {SUMMARY_CSV}")
    print(f"Total elapsed time        : {format_seconds(total_elapsed)}s")
    print("=" * 100)


if __name__ == "__main__":
    main()