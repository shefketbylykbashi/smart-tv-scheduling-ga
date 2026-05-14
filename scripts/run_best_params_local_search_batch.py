import csv
import json
import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# Paths
# ============================================================

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent

SOLVER_PATH = REPO_ROOT / "src" / "smart_tv_scheduler_ga2_with_local_search.py"
INSTANCES_DIR = REPO_ROOT / "instances"
RESULTS_DIR = REPO_ROOT / "results_ga_localsearch"
TABLES_DIR = REPO_ROOT / "tables"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = TABLES_DIR / "local_search_best_params_runs.csv"


# ============================================================
# Experiment settings
# ============================================================

EXECUTIONS_PER_INSTANCE = 10
TIME_LIMIT = 60
BASE_SEED = 42

# If you want only Kosovo, use:
# TARGET_INSTANCES = ["kosovo_tv_input"]
#
# If you want all instances with their best parameters, leave this:
TARGET_INSTANCES = [
    "germany_tv_input",
    "kosovo_tv_input",
    "netherlands_tv_input",
    "singapore_pw",
    "spain_iptv",
    "toy",
    "uk_iptv",
    "uk_tv_input",
    "us_iptv",
    "usa_tv_input",
    "youtube_gold",
    "youtube_premium",
]


# ============================================================
# Best parameters from previous parameter tuning
# ============================================================

BEST_PARAMS = {
    "australia_iptv": {
        "config_id": "C09",
        "top_k": 12,
        "population": 40,
        "elite": 3,
        "best_seed": 9123,
    },
    "canada_pw": {
        "config_id": "C03",
        "top_k": 12,
        "population": 24,
        "elite": 2,
        "best_seed": 3069,
    },
    "china_pw": {
        "config_id": "C02",
        "top_k": 10,
        "population": 24,
        "elite": 2,
        "best_seed": 2060,
    },
    "croatia_tv_input": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "france_iptv": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "germany_tv_input": {
        "config_id": "C04",
        "top_k": 8,
        "population": 32,
        "elite": 2,
        "best_seed": 4078,
    },
    "kosovo_tv_input": {
        "config_id": "C03",
        "top_k": 12,
        "population": 24,
        "elite": 2,
        "best_seed": 3069,
    },
    "netherlands_tv_input": {
        "config_id": "C02",
        "top_k": 10,
        "population": 24,
        "elite": 2,
        "best_seed": 2060,
    },
    "singapore_pw": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "spain_iptv": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "toy": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "uk_iptv": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "uk_tv_input": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "us_iptv": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "usa_tv_input": {
        "config_id": "C02",
        "top_k": 10,
        "population": 24,
        "elite": 2,
        "best_seed": 2060,
    },
    "youtube_gold": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
    "youtube_premium": {
        "config_id": "C01",
        "top_k": 8,
        "population": 24,
        "elite": 2,
        "best_seed": 1051,
    },
}


# ============================================================
# CSV fields
# ============================================================

FIELDNAMES = [
    "instance",
    "execution",
    "config_id",
    "top_k",
    "population",
    "elite",
    "seed",
    "time_limit_seconds",
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
    "local_search_used",
    "local_search_initial_score",
    "local_search_final_score",
    "local_search_gain",
    "local_search_iterations",
    "local_search_improvements",
    "local_search_runtime_seconds",
    "runtime_seconds",
    "output_file",
    "status",
    "error",
]


def append_csv_row(row):
    file_exists = CSV_PATH.exists()

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


def read_result_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_csv_row(
    instance_name,
    execution_idx,
    params,
    seed,
    output_path,
    status,
    error="",
):
    row = {
        "instance": instance_name,
        "execution": execution_idx,
        "config_id": params["config_id"],
        "top_k": params["top_k"],
        "population": params["population"],
        "elite": params["elite"],
        "seed": seed,
        "time_limit_seconds": TIME_LIMIT,
        "score": "",
        "feasible": "",
        "deterministic_seed_score": "",
        "ga_score": "",
        "switches": "",
        "partials": "",
        "bonus": "",
        "program_score": "",
        "revisits": "",
        "normalized_length": "",
        "local_search_used": "",
        "local_search_initial_score": "",
        "local_search_final_score": "",
        "local_search_gain": "",
        "local_search_iterations": "",
        "local_search_improvements": "",
        "local_search_runtime_seconds": "",
        "runtime_seconds": "",
        "output_file": str(output_path.relative_to(REPO_ROOT)) if output_path else "",
        "status": status,
        "error": error,
    }

    if status != "completed" or not output_path.exists():
        return row

    result = read_result_json(output_path)
    meta = result.get("meta", {})

    row.update({
        "score": result.get("total_score", ""),
        "feasible": meta.get("feasible", ""),
        "deterministic_seed_score": meta.get("deterministic_seed_score", ""),
        "ga_score": meta.get("ga_score", ""),
        "switches": meta.get("switches", ""),
        "partials": meta.get("partials", ""),
        "bonus": meta.get("bonus", ""),
        "program_score": meta.get("program_score", ""),
        "revisits": meta.get("revisits", ""),
        "normalized_length": meta.get("normalized_length", ""),
        "local_search_used": meta.get("local_search_used", ""),
        "local_search_initial_score": meta.get("local_search_initial_score", ""),
        "local_search_final_score": meta.get("local_search_final_score", ""),
        "local_search_gain": meta.get("local_search_gain", ""),
        "local_search_iterations": meta.get("local_search_iterations", ""),
        "local_search_improvements": meta.get("local_search_improvements", ""),
        "local_search_runtime_seconds": meta.get("local_search_runtime_seconds", ""),
        "runtime_seconds": meta.get("runtime_seconds", ""),
    })

    return row


def run_single_execution(instance_name, execution_idx, params):
    instance_path = INSTANCES_DIR / f"{instance_name}.json"

    if not instance_path.exists():
        output_path = None
        row = build_csv_row(
            instance_name=instance_name,
            execution_idx=execution_idx,
            params=params,
            seed="",
            output_path=output_path,
            status="missing_instance",
            error=f"Instance file not found: {instance_path}",
        )
        append_csv_row(row)
        print(f"      missing instance: {instance_path}")
        return

    seed = params["best_seed"] + 1009 * (execution_idx - 1)

    output_path = RESULTS_DIR / (
        f"{instance_name}_ls_exec_{execution_idx:02d}_{params['config_id']}.json"
    )

    cmd = [
        sys.executable,
        str(SOLVER_PATH),
        str(instance_path),
        str(output_path),
        "--runs",
        "1",
        "--time-limit",
        str(TIME_LIMIT),
        "--top-k",
        str(params["top_k"]),
        "--population",
        str(params["population"]),
        "--elite",
        str(params["elite"]),
        "--seed",
        str(seed),
    ]

    print(
        f"    Execution {execution_idx:02d}/{EXECUTIONS_PER_INSTANCE} | "
        f"{params['config_id']} | top_k={params['top_k']} | "
        f"population={params['population']} | elite={params['elite']} | seed={seed}"
    )

    start = time.time()

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )

        elapsed = time.time() - start

        if completed.returncode != 0:
            error_msg = completed.stderr.strip() or completed.stdout.strip()

            row = build_csv_row(
                instance_name=instance_name,
                execution_idx=execution_idx,
                params=params,
                seed=seed,
                output_path=output_path,
                status="error",
                error=error_msg,
            )
            append_csv_row(row)

            print(f"      ERROR after {round(elapsed, 2)}s")
            print(error_msg[:500])
            return

        row = build_csv_row(
            instance_name=instance_name,
            execution_idx=execution_idx,
            params=params,
            seed=seed,
            output_path=output_path,
            status="completed",
            error="",
        )
        append_csv_row(row)

        print(
            f"      completed | score={row['score']} | "
            f"ls_gain={row['local_search_gain']} | "
            f"time={round(elapsed, 2)}s | output={row['output_file']}"
        )

    except Exception as e:
        elapsed = time.time() - start

        row = build_csv_row(
            instance_name=instance_name,
            execution_idx=execution_idx,
            params=params,
            seed=seed,
            output_path=output_path,
            status="exception",
            error=str(e),
        )
        append_csv_row(row)

        print(f"      EXCEPTION after {round(elapsed, 2)}s: {e}")


def main():
    if not SOLVER_PATH.exists():
        raise FileNotFoundError(f"Solver not found: {SOLVER_PATH}")

    print("=" * 100)
    print("Running Local Search GA with best parameters")
    print(f"Solver       : {SOLVER_PATH}")
    print(f"Instances dir: {INSTANCES_DIR}")
    print(f"Results dir  : {RESULTS_DIR}")
    print(f"CSV          : {CSV_PATH}")
    print(f"Runs/instance: {EXECUTIONS_PER_INSTANCE}")
    print(f"Time limit   : {TIME_LIMIT}s per run")
    print("=" * 100)

    total_start = time.time()

    for idx, instance_name in enumerate(TARGET_INSTANCES, start=1):
        if instance_name not in BEST_PARAMS:
            print(f"\n[{idx}/{len(TARGET_INSTANCES)}] {instance_name}: missing best params")
            continue

        params = BEST_PARAMS[instance_name]

        print(
            f"\n[{idx}/{len(TARGET_INSTANCES)}] Instance: {instance_name} | "
            f"best_config={params['config_id']} | "
            f"top_k={params['top_k']} | population={params['population']} | elite={params['elite']}"
        )

        for execution_idx in range(1, EXECUTIONS_PER_INSTANCE + 1):
            run_single_execution(
                instance_name=instance_name,
                execution_idx=execution_idx,
                params=params,
            )

    total_elapsed = time.time() - total_start

    print("\n" + "=" * 100)
    print("Finished Local Search GA batch")
    print(f"Results saved in : {RESULTS_DIR}")
    print(f"CSV saved in     : {CSV_PATH}")
    print(f"Total time       : {round(total_elapsed, 2)}s")
    print("=" * 100)


if __name__ == "__main__":
    main()