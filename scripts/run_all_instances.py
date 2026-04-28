from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "smart_tv_scheduler_scoreboost.py"
INSTANCES = ROOT / "instances"
RESULTS = ROOT / "results"

FILES = [
    "australia_iptv.json",
    "canada_pw.json",
    "china_pw.json",
    "croatia_tv_input.json",
    "france_iptv.json",
    "germany_tv_input.json",
    "kosovo_tv_input.json",
    "netherlands_tv_input.json",
    "singapore_pw.json",
    "spain_iptv.json",
    "uk_iptv.json",
    "uk_tv_input.json",
    "us_iptv.json",
    "usa_tv_input.json",
    "youtube_gold.json",
    "youtube_premium.json",
]

RESULTS.mkdir(parents=True, exist_ok=True)

for name in FILES:
    input_file = INSTANCES / name
    output_name = name.replace("_input", "").replace(".json", "_output.json")
    output_file = RESULTS / output_name

    print(f"Running: {name}")
    subprocess.run(
        [sys.executable, str(SRC), str(input_file), str(output_file)],
        check=True
    )

print("Done.")