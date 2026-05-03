import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_GA_DIR = REPO_ROOT / "results_ga"
TABLES_DIR = REPO_ROOT / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = TABLES_DIR / "recovered_results_ga_parameter_tuning.csv"

fieldnames = [
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

rows = []

for path in sorted(RESULTS_GA_DIR.glob("*_ga_exec_*.json")):
    try:
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)

        meta = result.get("meta", {})
        tuning = result.get("parameter_tuning", {})

        rows.append({
            "instance": tuning.get("instance", path.stem),
            "execution": tuning.get("execution", ""),
            "config_id": tuning.get("config_id", ""),
            "score": result.get("total_score", ""),
            "feasible": meta.get("feasible", ""),
            "deterministic_seed_score": meta.get("deterministic_seed_score", ""),
            "ga_score": meta.get("ga_score", result.get("total_score", "")),
            "switches": meta.get("switches", ""),
            "partials": meta.get("partials", ""),
            "bonus": meta.get("bonus", ""),
            "program_score": meta.get("program_score", ""),
            "revisits": meta.get("revisits", ""),
            "normalized_length": meta.get("normalized_length", ""),
            "top_k": tuning.get("top_k", meta.get("top_k_segments_per_program", "")),
            "population_size": tuning.get("population_size", meta.get("population_size", "")),
            "elite_count": tuning.get("elite_count", meta.get("elite_count", "")),
            "seed": tuning.get("seed", meta.get("seed", "")),
            "time_limit_seconds": tuning.get("time_limit_seconds", meta.get("time_limit_seconds", "")),
            "allow_program_revisit": tuning.get("allow_program_revisit", meta.get("allow_program_revisit", "")),
            "revisit_penalty": tuning.get("revisit_penalty", meta.get("revisit_penalty", "")),
            "runtime_seconds": tuning.get("runtime_seconds", meta.get("runtime_seconds", "")),
            "output_file": str(path.relative_to(REPO_ROOT)),
            "error": "",
        })

    except Exception as e:
        rows.append({
            "instance": path.stem,
            "execution": "",
            "config_id": "",
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
            "top_k": "",
            "population_size": "",
            "elite_count": "",
            "seed": "",
            "time_limit_seconds": "",
            "allow_program_revisit": "",
            "revisit_penalty": "",
            "runtime_seconds": "",
            "output_file": str(path),
            "error": str(e),
        })

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Recovered CSV saved to: {OUTPUT_CSV}")
print(f"Rows recovered: {len(rows)}")