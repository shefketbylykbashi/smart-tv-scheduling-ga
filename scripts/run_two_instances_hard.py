import csv
import json
import multiprocessing as mp
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


# ------------------------------------------------------------
# Imports from your GA implementation
# ------------------------------------------------------------
from smart_tv_scheduler_ga2 import (  # noqa: E402
    build_segments,
    keep_top_k_per_program,
    improve_unique_programs,
    HybridGAScheduler,
)


# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
INSTANCES_DIR = REPO_ROOT / "instances"
RESULTS_GA_DIR = REPO_ROOT / "results_ga"
TABLES_DIR = REPO_ROOT / "tables"

RESULTS_GA_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)

DETAILED_CSV = TABLES_DIR / "two_instances_hard60_best_so_far_results.csv"

# ------------------------------------------------------------
# Put here only the two instances you want to run.
# Use file names WITHOUT .json
# Example:
#   instances/youtube_gold.json    -> "youtube_gold"
#   instances/youtube_premium.json -> "youtube_premium"
# ------------------------------------------------------------
TARGET_INSTANCES = [
    "youtube_gold",
    "youtube_premium",
]

EXECUTIONS_PER_INSTANCE = 10
HARD_TIMEOUT_SECONDS = 300
BASE_SEED = 42

ALLOW_PROGRAM_REVISIT = False
REVISIT_PENALTY = 25

# For heavy instances, keep these configurations lighter.
# If you use top_k=15 and population=40, many large instances may not return
# anything useful within 60 seconds.
PARAMETER_CONFIGS = [
    {"config_id": "C01", "top_k": 5, "population_size": 12, "elite_count": 1},
    {"config_id": "C02", "top_k": 6, "population_size": 12, "elite_count": 1},
    {"config_id": "C03", "top_k": 8, "population_size": 16, "elite_count": 1},
    {"config_id": "C04", "top_k": 5, "population_size": 16, "elite_count": 2},
    {"config_id": "C05", "top_k": 6, "population_size": 16, "elite_count": 2},
    {"config_id": "C06", "top_k": 8, "population_size": 20, "elite_count": 2},
    {"config_id": "C07", "top_k": 5, "population_size": 20, "elite_count": 2},
    {"config_id": "C08", "top_k": 6, "population_size": 24, "elite_count": 2},
    {"config_id": "C09", "top_k": 8, "population_size": 24, "elite_count": 2},
    {"config_id": "C10", "top_k": 10, "population_size": 24, "elite_count": 2},
]


FIELDNAMES = [
    "instance",
    "execution",
    "config_id",
    "status",
    "solution_source",
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
    "hard_timeout_seconds",
    "runtime_seconds",
    "output_file",
    "error",
]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def append_csv_row(row):
    file_exists = DETAILED_CSV.exists()

    with open(DETAILED_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


def make_empty_result(
    seed,
    population_size,
    elite_count,
    top_k,
    runtime_seconds,
    solution_source,
):
    return {
        "scheduled_programs": [],
        "total_score": 0,
        "meta": {
            "seed": seed,
            "feasible": True,
            "population_size": population_size,
            "elite_count": elite_count,
            "time_limit_seconds": HARD_TIMEOUT_SECONDS,
            "runtime_seconds": round(runtime_seconds, 4),
            "deterministic_seed_score": 0,
            "ga_score": 0,
            "switches": 0,
            "partials": 0,
            "bonus": 0,
            "program_score": 0,
            "revisits": 0,
            "normalized_length": 0,
            "top_k_segments_per_program": top_k,
            "allow_program_revisit": ALLOW_PROGRAM_REVISIT,
            "revisit_penalty": REVISIT_PENALTY,
            "solution_source": solution_source,
        },
    }


def schedule_to_result(
    schedule,
    evaluation,
    deterministic_score,
    seed,
    population_size,
    elite_count,
    top_k,
    runtime_seconds,
    solution_source,
):
    return {
        "scheduled_programs": [
            {
                "program_id": s["program_id"],
                "channel_id": s["channel_id"],
                "start": s["seg_start"],
                "end": s["seg_end"],
            }
            for s in schedule
        ],
        "total_score": int(evaluation["score"]),
        "meta": {
            "seed": seed,
            "feasible": evaluation["feasible"],
            "population_size": population_size,
            "elite_count": elite_count,
            "time_limit_seconds": HARD_TIMEOUT_SECONDS,
            "runtime_seconds": round(runtime_seconds, 4),
            "deterministic_seed_score": int(deterministic_score),
            "ga_score": int(evaluation["score"]),
            "switches": int(evaluation["switches"]),
            "partials": int(evaluation["partials"]),
            "bonus": int(evaluation["bonus"]),
            "program_score": int(evaluation["program_score"]),
            "revisits": int(evaluation["revisits"]),
            "normalized_length": int(evaluation["normalized_length"]),
            "top_k_segments_per_program": top_k,
            "allow_program_revisit": ALLOW_PROGRAM_REVISIT,
            "revisit_penalty": REVISIT_PENALTY,
            "solution_source": solution_source,
        },
    }


# ------------------------------------------------------------
# Child process worker
# ------------------------------------------------------------
def worker_run_best_so_far(queue, data, params):
    """
    Runs inside a child process.

    It sends a deterministic fallback result as soon as it is available.
    Then, if GA finishes before the hard timeout, it sends a better final result.

    The parent process may kill this worker at 60 seconds, but any result already
    sent to the queue can still be saved.
    """
    start = time.time()

    try:
        top_k = params["top_k"]
        population_size = params["population_size"]
        elite_count = params["elite_count"]
        seed = params["seed"]
        allow_program_revisit = params["allow_program_revisit"]
        revisit_penalty = params["revisit_penalty"]

        # --------------------------------------------------------
        # 1. Build candidate segments
        # --------------------------------------------------------
        segments = build_segments(data)

        if not segments:
            result = make_empty_result(
                seed=seed,
                population_size=population_size,
                elite_count=elite_count,
                top_k=top_k,
                runtime_seconds=time.time() - start,
                solution_source="no_valid_segments",
            )

            queue.put({
                "ok": True,
                "result": result,
            })
            return

        # --------------------------------------------------------
        # 2. Prune candidates
        # --------------------------------------------------------
        segments = keep_top_k_per_program(segments, top_k=top_k)

        # --------------------------------------------------------
        # 3. Build deterministic fallback
        #    max_iters reduced from 40 to 5 for 60-second experiments.
        # --------------------------------------------------------
        deterministic_schedule, deterministic_score = improve_unique_programs(
            segments,
            R=data["max_consecutive_genre"],
            S=data["switch_penalty"],
            max_iters=5,
        )

        # --------------------------------------------------------
        # 4. Build GA object mainly to reuse Evaluator normalization/evaluation
        # --------------------------------------------------------
        ga = HybridGAScheduler(
            data=data,
            segments=segments,
            deterministic_seed=deterministic_schedule,
            population_size=population_size,
            elite_count=elite_count,
            seed=seed,
            allow_program_revisit=allow_program_revisit,
            revisit_penalty=revisit_penalty,
        )

        deterministic_schedule = ga.ev.normalize_schedule(deterministic_schedule)
        deterministic_eval = ga.ev.evaluate(deterministic_schedule)

        fallback_result = schedule_to_result(
            schedule=deterministic_schedule,
            evaluation=deterministic_eval,
            deterministic_score=deterministic_score,
            seed=seed,
            population_size=population_size,
            elite_count=elite_count,
            top_k=top_k,
            runtime_seconds=time.time() - start,
            solution_source="deterministic_fallback_before_ga",
        )

        # Send fallback immediately.
        queue.put({
            "ok": True,
            "result": fallback_result,
        })

        # --------------------------------------------------------
        # 5. Run GA only with remaining time
        # --------------------------------------------------------
        elapsed = time.time() - start
        remaining_time = max(0.0, HARD_TIMEOUT_SECONDS - elapsed)

        if remaining_time <= 1.0:
            return

        best_schedule, best_eval = ga.evolve(time_limit_seconds=remaining_time)
        normalized_best = ga.ev.normalize_schedule(best_schedule)

        final_result = schedule_to_result(
            schedule=normalized_best,
            evaluation=best_eval,
            deterministic_score=deterministic_score,
            seed=seed,
            population_size=population_size,
            elite_count=elite_count,
            top_k=top_k,
            runtime_seconds=time.time() - start,
            solution_source="ga_completed",
        )

        queue.put({
            "ok": True,
            "result": final_result,
        })

    except Exception as e:
        queue.put({
            "ok": False,
            "error": str(e),
        })


# ------------------------------------------------------------
# Hard timeout runner
# ------------------------------------------------------------
def run_with_hard_timeout_best_so_far(data, params, timeout_seconds):
    queue = mp.Queue()

    process = mp.Process(
        target=worker_run_best_so_far,
        args=(queue, data, params),
    )

    start = time.time()
    process.start()

    latest_payload = None

    while process.is_alive():
        process.join(timeout=0.5)

        while not queue.empty():
            latest_payload = queue.get()

        if time.time() - start >= timeout_seconds:
            process.terminate()
            process.join()

            runtime = time.time() - start

            if latest_payload and latest_payload.get("ok"):
                return {
                    "status": "time_limit_returned_best_so_far",
                    "runtime_seconds": round(runtime, 4),
                    "result": latest_payload["result"],
                    "error": "",
                }

            return {
                "status": "time_limit_no_solution_yet",
                "runtime_seconds": round(runtime, 4),
                "result": None,
                "error": "",
            }

    runtime = time.time() - start

    while not queue.empty():
        latest_payload = queue.get()

    if latest_payload and latest_payload.get("ok"):
        return {
            "status": "completed",
            "runtime_seconds": round(runtime, 4),
            "result": latest_payload["result"],
            "error": "",
        }

    if latest_payload and not latest_payload.get("ok"):
        return {
            "status": "error",
            "runtime_seconds": round(runtime, 4),
            "result": None,
            "error": latest_payload.get("error", ""),
        }

    return {
        "status": "time_limit_no_solution_yet",
        "runtime_seconds": round(runtime, 4),
        "result": None,
        "error": "",
    }


def make_csv_row(
    instance_name,
    execution_idx,
    config,
    seed,
    run_status,
    output_file="",
):
    result = run_status.get("result")
    meta = result.get("meta", {}) if result else {}

    return {
        "instance": instance_name,
        "execution": execution_idx,
        "config_id": config["config_id"],
        "status": run_status["status"],
        "solution_source": meta.get("solution_source", ""),
        "score": result.get("total_score", "") if result else "",
        "feasible": meta.get("feasible", ""),
        "deterministic_seed_score": meta.get("deterministic_seed_score", ""),
        "ga_score": meta.get("ga_score", ""),
        "switches": meta.get("switches", ""),
        "partials": meta.get("partials", ""),
        "bonus": meta.get("bonus", ""),
        "program_score": meta.get("program_score", ""),
        "revisits": meta.get("revisits", ""),
        "normalized_length": meta.get("normalized_length", ""),
        "top_k": config["top_k"],
        "population_size": config["population_size"],
        "elite_count": config["elite_count"],
        "seed": seed,
        "hard_timeout_seconds": HARD_TIMEOUT_SECONDS,
        "runtime_seconds": run_status["runtime_seconds"],
        "output_file": output_file,
        "error": run_status["error"],
    }


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    print("=" * 100)
    print("Running selected instances with HARD 60-second timeout per execution")
    print("If 60 seconds is reached, the latest generated solution is saved.")
    print(f"Target instances : {TARGET_INSTANCES}")
    print(f"CSV              : {DETAILED_CSV}")
    print(f"Results dir      : {RESULTS_GA_DIR}")
    print("=" * 100)

    for instance_name in TARGET_INSTANCES:
        instance_path = INSTANCES_DIR / f"{instance_name}.json"

        if not instance_path.exists():
            print(f"\nMissing instance: {instance_path}")

            row = {
                "instance": instance_name,
                "execution": "",
                "config_id": "",
                "status": "missing_instance",
                "solution_source": "",
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
                "top_k": "",
                "population_size": "",
                "elite_count": "",
                "seed": "",
                "hard_timeout_seconds": HARD_TIMEOUT_SECONDS,
                "runtime_seconds": "",
                "output_file": "",
                "error": f"File not found: {instance_path}",
            }

            append_csv_row(row)
            continue

        data = load_json(instance_path)

        print(f"\nInstance: {instance_name}")

        for execution_idx in range(1, EXECUTIONS_PER_INSTANCE + 1):
            config = PARAMETER_CONFIGS[(execution_idx - 1) % len(PARAMETER_CONFIGS)]
            seed = BASE_SEED + 1009 * execution_idx

            params = {
                "top_k": config["top_k"],
                "population_size": config["population_size"],
                "elite_count": config["elite_count"],
                "seed": seed,
                "allow_program_revisit": ALLOW_PROGRAM_REVISIT,
                "revisit_penalty": REVISIT_PENALTY,
            }

            output_path = RESULTS_GA_DIR / (
                f"{instance_name}_hard60_exec_{execution_idx:02d}_{config['config_id']}.json"
            )

            print(
                f"  Execution {execution_idx:02d}/{EXECUTIONS_PER_INSTANCE} | "
                f"{config['config_id']} | top_k={config['top_k']} | "
                f"pop={config['population_size']} | elite={config['elite_count']} | seed={seed}"
            )

            run_status = run_with_hard_timeout_best_so_far(
                data=data,
                params=params,
                timeout_seconds=HARD_TIMEOUT_SECONDS,
            )

            output_file = ""

            if run_status["result"] is not None:
                result = run_status["result"]

                result["hard_timeout_experiment"] = {
                    "instance": instance_name,
                    "execution": execution_idx,
                    "config_id": config["config_id"],
                    "top_k": config["top_k"],
                    "population_size": config["population_size"],
                    "elite_count": config["elite_count"],
                    "seed": seed,
                    "hard_timeout_seconds": HARD_TIMEOUT_SECONDS,
                    "runtime_seconds": run_status["runtime_seconds"],
                    "status": run_status["status"],
                }

                save_json(output_path, result)
                output_file = str(output_path.relative_to(REPO_ROOT))

                print(
                    f"      {run_status['status']} | "
                    f"source={result.get('meta', {}).get('solution_source')} | "
                    f"score={result.get('total_score')} | "
                    f"time={run_status['runtime_seconds']}s"
                )

            else:
                print(
                    f"      {run_status['status']} | "
                    f"no solution generated yet | "
                    f"time={run_status['runtime_seconds']}s"
                )

            row = make_csv_row(
                instance_name=instance_name,
                execution_idx=execution_idx,
                config=config,
                seed=seed,
                run_status=run_status,
                output_file=output_file,
            )

            append_csv_row(row)

    print("\n" + "=" * 100)
    print("Finished hard-timeout best-so-far experiment")
    print(f"CSV saved to         : {DETAILED_CSV}")
    print(f"JSON outputs saved to: {RESULTS_GA_DIR}")
    print("=" * 100)


if __name__ == "__main__":
    mp.freeze_support()
    main()