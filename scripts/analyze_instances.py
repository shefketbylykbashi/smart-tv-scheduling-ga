#!/usr/bin/env python3
"""
Analyze Smart TV scheduling instances.

Usage:
    python analyze_instances.py instances/australia_iptv.json
    python analyze_instances.py instances/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import Counter
from typing import Any, Dict, List


def load_instance(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def classify_constraints(data: Dict[str, Any]) -> Dict[str, List[str]]:
    hard = [
        "Operating horizon: opening_time .. closing_time",
        "Minimum display duration: min_duration",
        "Maximum consecutive same-genre selections: max_consecutive_genre",
        "Priority-block channel restrictions: priority_blocks.allowed_channels",
        "Temporal feasibility of selected segments",
        "Non-overlap of selected schedule segments",
    ]

    soft = [
        "Program utility: program score",
        "Genre-time preference bonuses: time_preferences.bonus",
        "Channel-switch penalty: switch_penalty",
        "Early start / early stop truncation penalty: termination_penalty",
    ]

    return {"hard": hard, "soft": soft}


def summarize_instance(data: Dict[str, Any], name: str) -> Dict[str, Any]:
    channels = data.get("channels", [])
    priority_blocks = data.get("priority_blocks", [])
    time_prefs = data.get("time_preferences", [])

    channel_count = len(channels)
    program_count = 0
    genre_counter: Counter[str] = Counter()
    durations: List[int] = []
    scores: List[float] = []

    for ch in channels:
        programs = ch.get("programs", [])
        program_count += len(programs)
        for p in programs:
            genre_counter[p.get("genre", "UNKNOWN")] += 1
            duration = p.get("end", 0) - p.get("start", 0)
            durations.append(duration)
            scores.append(p.get("score", 0))

    opening = data.get("opening_time")
    closing = data.get("closing_time")
    window = (closing - opening) if opening is not None and closing is not None else None

    avg_programs_per_channel = program_count / channel_count if channel_count else 0
    avg_duration = sum(durations) / len(durations) if durations else 0
    avg_score = sum(scores) / len(scores) if scores else 0

    allowed_sizes = [
        len(block.get("allowed_channels", []))
        for block in priority_blocks
    ]
    avg_allowed_channels = (
        sum(allowed_sizes) / len(allowed_sizes) if allowed_sizes else 0
    )

    summary = {
        "instance": name,
        "opening_time": opening,
        "closing_time": closing,
        "window_length": window,
        "channel_count": channel_count,
        "program_count": program_count,
        "avg_programs_per_channel": round(avg_programs_per_channel, 2),
        "genre_count": len(genre_counter),
        "top_genres": genre_counter.most_common(10),
        "avg_program_duration": round(avg_duration, 2),
        "avg_program_score": round(avg_score, 2),
        "min_duration": data.get("min_duration"),
        "max_consecutive_genre": data.get("max_consecutive_genre"),
        "switch_penalty": data.get("switch_penalty"),
        "termination_penalty": data.get("termination_penalty"),
        "priority_block_count": len(priority_blocks),
        "avg_allowed_channels_per_priority_block": round(avg_allowed_channels, 2),
        "time_preference_count": len(time_prefs),
        "constraints": classify_constraints(data),
    }
    return summary


def print_summary(summary: Dict[str, Any]) -> None:
    print("=" * 80)
    print(f"Instance: {summary['instance']}")
    print("=" * 80)
    print(f"Operating window       : {summary['opening_time']} -> {summary['closing_time']} "
          f"(length={summary['window_length']})")
    print(f"Channels               : {summary['channel_count']}")
    print(f"Programs               : {summary['program_count']}")
    print(f"Avg. programs/channel  : {summary['avg_programs_per_channel']}")
    print(f"Genres                 : {summary['genre_count']}")
    print(f"Avg. program duration  : {summary['avg_program_duration']}")
    print(f"Avg. program score     : {summary['avg_program_score']}")
    print()

    print("Hard constraints")
    for item in summary["constraints"]["hard"]:
        print(f"  - {item}")
    print()

    print("Soft constraints / objective terms")
    for item in summary["constraints"]["soft"]:
        print(f"  - {item}")
    print()

    print("Constraint parameters")
    print(f"  - min_duration               : {summary['min_duration']}")
    print(f"  - max_consecutive_genre      : {summary['max_consecutive_genre']}")
    print(f"  - switch_penalty             : {summary['switch_penalty']}")
    print(f"  - termination_penalty        : {summary['termination_penalty']}")
    print(f"  - priority blocks            : {summary['priority_block_count']}")
    print(f"  - avg allowed channels/block : {summary['avg_allowed_channels_per_priority_block']}")
    print(f"  - time preferences           : {summary['time_preference_count']}")
    print()

    print("Top genres")
    for genre, count in summary["top_genres"]:
        print(f"  - {genre}: {count}")
    print()


def analyze_path(path: Path) -> None:
    if path.is_file():
        data = load_instance(path)
        summary = summarize_instance(data, path.name)
        print_summary(summary)
        return

    if path.is_dir():
        files = sorted(path.glob("*.json"))
        if not files:
            print("No JSON files found.")
            return

        all_rows = []
        for file in files:
            data = load_instance(file)
            summary = summarize_instance(data, file.name)
            all_rows.append(summary)
            print_summary(summary)

        print("=" * 80)
        print("Compact overview")
        print("=" * 80)
        print(
            f"{'Instance':30} {'Channels':>8} {'Programs':>10} "
            f"{'Genres':>8} {'Pref':>6} {'PBlocks':>8}"
        )
        for row in all_rows:
            print(
                f"{row['instance']:30} {row['channel_count']:8} {row['program_count']:10} "
                f"{row['genre_count']:8} {row['time_preference_count']:6} "
                f"{row['priority_block_count']:8}"
            )
        return

    print(f"Path not found: {path}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python analyze_instances.py <instance.json | folder>")
        sys.exit(1)

    path = Path(sys.argv[1])
    analyze_path(path)


if __name__ == "__main__":
    main()