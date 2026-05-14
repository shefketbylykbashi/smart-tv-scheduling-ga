import argparse
import json
import math
import random
import time
from collections import defaultdict

from smart_tv_scheduler_scoreboost import (
    build_segments,
    keep_top_k_per_program,
    improve_unique_programs,
    channel_allowed,
    compute_bonus,
)

NEG_INF = -10**18


# ============================================================
# Utility helpers
# ============================================================

def deep_copy_schedule(schedule):
    return [dict(x) for x in schedule]


def schedule_key(schedule):
    return tuple(
        (
            s["program_id"],
            s["channel_id"],
            s["seg_start"],
            s["seg_end"],
        )
        for s in schedule
    )


def segment_key(s):
    return (
        s["program_id"],
        s["channel_id"],
        s["seg_start"],
        s["seg_end"],
    )


def seg_value(seg):
    return seg["score"] + seg["bonus"] - seg["cut_penalty"]


def effective_duration(seg):
    return seg["seg_end"] - seg["seg_start"]


def interval_overlap_len(a1, a2, b1, b2):
    return max(0, min(a2, b2) - max(a1, b1))


def random_choice_or_none(items, rng):
    if not items:
        return None
    return items[rng.randrange(len(items))]


# ============================================================
# Candidate pool
# ============================================================

class CandidatePool:
    def __init__(self, segments):
        self.all_segments = [dict(s) for s in segments]
        self.by_program = defaultdict(list)
        self.by_channel = defaultdict(list)
        self.by_genre = defaultdict(list)

        for s in self.all_segments:
            self.by_program[s["program_id"]].append(s)
            self.by_channel[s["channel_id"]].append(s)
            self.by_genre[s["genre"]].append(s)

        self.all_segments.sort(
            key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"])
        )

        for bucket in self.by_program.values():
            bucket.sort(key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"]))
        for bucket in self.by_channel.values():
            bucket.sort(key=lambda x: (x["seg_start"], x["seg_end"], x["program_id"]))
        for bucket in self.by_genre.values():
            bucket.sort(key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"]))

    def time_nearby(self, start, end, slack=40):
        lo = start - slack
        hi = end + slack
        return [
            s for s in self.all_segments
            if s["seg_end"] > lo and s["seg_start"] < hi
        ]

    def gap_candidates(self, gap_start, gap_end, limit=80):
        cands = [
            s for s in self.all_segments
            if s["seg_start"] >= gap_start and s["seg_end"] <= gap_end
        ]
        cands.sort(key=lambda x: (-seg_value(x), x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"]))
        return cands[:limit]

    def alternatives_for_segment(self, seg, slack=45, limit=80):
        cands = [
            s for s in self.time_nearby(seg["seg_start"], seg["seg_end"], slack=slack)
            if not (
                s["seg_start"] == seg["seg_start"]
                and s["seg_end"] == seg["seg_end"]
                and s["program_id"] == seg["program_id"]
                and s["channel_id"] == seg["channel_id"]
            )
        ]
        cands.sort(
            key=lambda x: (
                -seg_value(x),
                abs(x["seg_start"] - seg["seg_start"]),
                abs(x["seg_end"] - seg["seg_end"]),
                x["channel_id"],
                x["program_id"],
            )
        )
        return cands[:limit]

    def channel_continuation_candidates(self, prev_seg, next_seg=None, limit=80):
        """
        Candidates useful for local search: prefer same channel after prev_seg,
        optionally before next_seg, to reduce switching penalties.
        """
        if prev_seg is None:
            return []

        channel = prev_seg["channel_id"]
        start = prev_seg["seg_end"]
        end = next_seg["seg_start"] if next_seg is not None else None

        cands = []
        for s in self.by_channel.get(channel, []):
            if s["seg_start"] < start:
                continue
            if end is not None and s["seg_end"] > end:
                continue
            cands.append(s)

        cands.sort(key=lambda x: (-seg_value(x), x["seg_start"], x["seg_end"], x["program_id"]))
        return cands[:limit]


# ============================================================
# Evaluation and normalization
# ============================================================

class Evaluator:
    def __init__(self, data, allow_program_revisit=False, revisit_penalty=25):
        self.data = data
        self.O = data["opening_time"]
        self.E = data["closing_time"]
        self.D = data["min_duration"]
        self.R = data["max_consecutive_genre"]
        self.S = data["switch_penalty"]
        self.T = data["termination_penalty"]
        self.priority_blocks = data.get("priority_blocks", [])
        self.time_prefs = data.get("time_preferences", [])

        self.allow_program_revisit = allow_program_revisit
        self.revisit_penalty = revisit_penalty

    def recompute_segment_fields(self, s):
        s = dict(s)

        cut_penalty = 0
        if s["seg_start"] > s["prog_start"]:
            cut_penalty += self.T
        if s["seg_end"] < s["prog_end"]:
            cut_penalty += self.T

        s["cut_penalty"] = cut_penalty
        s["bonus"] = compute_bonus(
            s["seg_start"],
            s["seg_end"],
            s["genre"],
            self.D,
            self.time_prefs,
        )
        return s

    def segment_valid_basic(self, s):
        if s["seg_start"] < self.O or s["seg_end"] > self.E or s["seg_end"] <= s["seg_start"]:
            return False

        prog_len = s["prog_end"] - s["prog_start"]
        seg_len = s["seg_end"] - s["seg_start"]

        if prog_len < self.D:
            if not (s["seg_start"] == s["prog_start"] and s["seg_end"] == s["prog_end"]):
                return False
        else:
            if seg_len < self.D:
                return False

        if not channel_allowed(s["channel_id"], s["seg_start"], s["seg_end"], self.priority_blocks):
            return False

        return True

    def normalize_schedule(self, schedule):
        if not schedule:
            return []

        sched = [self.recompute_segment_fields(dict(s)) for s in schedule]
        sched = [s for s in sched if self.segment_valid_basic(s)]
        if not sched:
            return []

        sched.sort(key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"]))

        uniq = {}
        for s in sched:
            uniq[segment_key(s)] = s
        sched = list(uniq.values())
        sched.sort(key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"]))

        merged = []
        for cur in sched:
            if not merged:
                merged.append(dict(cur))
                continue

            last = merged[-1]
            if (
                last["program_id"] == cur["program_id"]
                and last["channel_id"] == cur["channel_id"]
                and last["seg_end"] == cur["seg_start"]
            ):
                last["seg_end"] = cur["seg_end"]
                last = self.recompute_segment_fields(last)
                merged[-1] = last
            else:
                merged.append(dict(cur))

        sched = merged

        if not self.allow_program_revisit:
            best_by_program = {}
            for s in sched:
                pid = s["program_id"]
                if pid not in best_by_program:
                    best_by_program[pid] = s
                else:
                    a = best_by_program[pid]
                    va = seg_value(a)
                    vb = seg_value(s)
                    if vb > va or (vb == va and effective_duration(s) > effective_duration(a)):
                        best_by_program[pid] = s

            kept_keys = {segment_key(s) for s in best_by_program.values()}
            sched = [s for s in sched if segment_key(s) in kept_keys]
            sched.sort(key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"]))

        return sched

    def evaluate(self, schedule, require_feasible=True):
        if not schedule:
            return {
                "feasible": True,
                "score": 0,
                "switches": 0,
                "partials": 0,
                "bonus": 0,
                "program_score": 0,
                "revisits": 0,
                "normalized_length": 0,
            }

        sched = self.normalize_schedule(schedule)

        if not sched:
            return {
                "feasible": True,
                "score": 0,
                "switches": 0,
                "partials": 0,
                "bonus": 0,
                "program_score": 0,
                "revisits": 0,
                "normalized_length": 0,
            }

        if require_feasible:
            for s in sched:
                if not self.segment_valid_basic(s):
                    return {
                        "feasible": False,
                        "score": NEG_INF,
                        "switches": 0,
                        "partials": 0,
                        "bonus": 0,
                        "program_score": 0,
                        "revisits": 0,
                        "normalized_length": 0,
                    }

            for i in range(1, len(sched)):
                if sched[i]["seg_start"] < sched[i - 1]["seg_end"]:
                    return {
                        "feasible": False,
                        "score": NEG_INF,
                        "switches": 0,
                        "partials": 0,
                        "bonus": 0,
                        "program_score": 0,
                        "revisits": 0,
                        "normalized_length": 0,
                    }

            streak = 1
            for i in range(1, len(sched)):
                if sched[i]["genre"] == sched[i - 1]["genre"]:
                    streak += 1
                    if streak > self.R:
                        return {
                            "feasible": False,
                            "score": NEG_INF,
                            "switches": 0,
                            "partials": 0,
                            "bonus": 0,
                            "program_score": 0,
                            "revisits": 0,
                            "normalized_length": 0,
                        }
                else:
                    streak = 1

        total_program_score = 0
        total_bonus = 0
        switches = 0
        partials = 0

        seen_programs = set()
        revisits = 0

        for i, s in enumerate(sched):
            total_program_score += s["score"]
            total_bonus += s["bonus"]

            if s["seg_start"] > s["prog_start"]:
                partials += 1
            if s["seg_end"] < s["prog_end"]:
                partials += 1

            if i > 0 and sched[i - 1]["channel_id"] != s["channel_id"]:
                switches += 1

            if s["program_id"] in seen_programs:
                revisits += 1
            seen_programs.add(s["program_id"])

        total = total_program_score + total_bonus - self.S * switches - self.T * partials

        if self.allow_program_revisit and revisits > 0:
            total -= revisits * self.revisit_penalty

        return {
            "feasible": True,
            "score": total,
            "switches": switches,
            "partials": partials,
            "bonus": total_bonus,
            "program_score": total_program_score,
            "revisits": revisits,
            "normalized_length": len(sched),
        }

    def marginal_contribution(self, schedule, idx):
        if idx < 0 or idx >= len(schedule):
            return -10**9

        base_eval = self.evaluate(schedule)
        if not base_eval["feasible"]:
            return -10**9

        reduced = deep_copy_schedule(schedule)
        reduced.pop(idx)
        red_eval = self.evaluate(reduced)
        if not red_eval["feasible"]:
            return -10**9

        return base_eval["score"] - red_eval["score"]


# ============================================================
# Repair engine
# ============================================================

class RepairEngine:
    def __init__(self, evaluator, pool):
        self.ev = evaluator
        self.pool = pool

    def _compatible_with_prefix(self, prefix, cand):
        cand = self.ev.recompute_segment_fields(cand)
        if not self.ev.segment_valid_basic(cand):
            return False

        if not prefix:
            return True

        last = prefix[-1]

        if cand["seg_start"] < last["seg_end"]:
            return False

        if not self.ev.allow_program_revisit:
            used_programs = {x["program_id"] for x in prefix}
            if cand["program_id"] in used_programs:
                return False

        streak = 1
        if cand["genre"] == last["genre"]:
            streak = 2
            j = len(prefix) - 2
            while j >= 0 and prefix[j]["genre"] == cand["genre"]:
                streak += 1
                j -= 1
            if streak > self.ev.R:
                return False

        return True

    def _drop_conflicts_by_value(self, schedule):
        sched = self.ev.normalize_schedule(schedule)
        changed = True

        while changed:
            changed = False
            sched.sort(key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"]))

            i = 1
            while i < len(sched):
                a = sched[i - 1]
                b = sched[i]
                if b["seg_start"] < a["seg_end"]:
                    va = seg_value(a)
                    vb = seg_value(b)

                    if va < vb:
                        sched.pop(i - 1)
                    elif vb < va:
                        sched.pop(i)
                    else:
                        if a["seg_end"] <= b["seg_end"]:
                            sched.pop(i)
                        else:
                            sched.pop(i - 1)

                    sched = self.ev.normalize_schedule(sched)
                    changed = True
                    break
                i += 1

        return self.ev.normalize_schedule(sched)

    def _greedy_select(self, candidates):
        ordered = self.ev.normalize_schedule(candidates)
        ordered.sort(
            key=lambda x: (
                x["seg_start"],
                x["seg_end"],
                -seg_value(x),
                x["channel_id"],
                x["program_id"],
            )
        )

        result = []
        for cand in ordered:
            if self._compatible_with_prefix(result, cand):
                result.append(dict(cand))

        return self.ev.normalize_schedule(result)

    def _fix_genre_runs(self, schedule):
        sched = self.ev.normalize_schedule(schedule)
        changed = True

        while changed:
            changed = False
            if not sched:
                break

            i = 0
            while i < len(sched):
                j = i + 1
                while j < len(sched) and sched[j]["genre"] == sched[i]["genre"]:
                    j += 1

                run_len = j - i
                if run_len > self.ev.R:
                    block = [(seg_value(sched[k]), k) for k in range(i, j)]
                    block.sort(key=lambda x: (x[0], -effective_duration(sched[x[1]])))
                    _, idx_to_remove = block[0]
                    sched.pop(idx_to_remove)
                    sched = self.ev.normalize_schedule(sched)
                    changed = True
                    break

                i = j

        return self.ev.normalize_schedule(sched)

    def _remove_duplicate_program_usage(self, schedule):
        sched = self.ev.normalize_schedule(schedule)

        if self.ev.allow_program_revisit:
            return sched

        best_by_program = {}
        for i, s in enumerate(sched):
            pid = s["program_id"]
            value = seg_value(s)
            if pid not in best_by_program:
                best_by_program[pid] = (value, effective_duration(s), i, s)
            else:
                prev = best_by_program[pid]
                cur = (value, effective_duration(s), i, s)
                if cur[0] > prev[0] or (cur[0] == prev[0] and cur[1] > prev[1]):
                    best_by_program[pid] = cur

        keep_keys = {segment_key(v[3]) for v in best_by_program.values()}
        sched = [s for s in sched if segment_key(s) in keep_keys]
        return self.ev.normalize_schedule(sched)

    def _fill_gaps(self, schedule, rounds=2, candidate_limit=120):
        sched = self.ev.normalize_schedule(schedule)

        for _ in range(rounds):
            sched.sort(key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"]))

            gaps = []
            cur = self.ev.O
            for s in sched:
                if cur < s["seg_start"]:
                    gaps.append((cur, s["seg_start"]))
                cur = max(cur, s["seg_end"])
            if cur < self.ev.E:
                gaps.append((cur, self.ev.E))

            inserted_any = False

            for gs, ge in gaps:
                if ge - gs < self.ev.D:
                    continue

                cands = self.pool.gap_candidates(gs, ge, limit=candidate_limit)
                for cand in cands:
                    if not self.ev.allow_program_revisit:
                        used_programs = {x["program_id"] for x in sched}
                        if cand["program_id"] in used_programs:
                            continue

                    trial = sched + [cand]
                    trial = self._drop_conflicts_by_value(trial)
                    trial = self._remove_duplicate_program_usage(trial)
                    trial = self._fix_genre_runs(trial)
                    trial = self._greedy_select(trial)

                    ev_trial = self.ev.evaluate(trial)
                    ev_cur = self.ev.evaluate(sched)

                    if ev_trial["feasible"] and ev_trial["score"] > ev_cur["score"]:
                        sched = trial
                        inserted_any = True
                        break

            if not inserted_any:
                break

        return self.ev.normalize_schedule(sched)

    def repair(self, schedule):
        if not schedule:
            return []

        sched = self.ev.normalize_schedule(schedule)
        if not sched:
            return []

        sched = self._drop_conflicts_by_value(sched)
        sched = self._remove_duplicate_program_usage(sched)
        sched = self._greedy_select(sched)
        sched = self._fix_genre_runs(sched)
        sched = self._greedy_select(sched)
        sched = self._fill_gaps(sched, rounds=3)
        sched = self._drop_conflicts_by_value(sched)
        sched = self._remove_duplicate_program_usage(sched)
        sched = self._greedy_select(sched)
        sched = self._fix_genre_runs(sched)
        sched = self._greedy_select(sched)

        ev = self.ev.evaluate(sched)
        if ev["feasible"]:
            return self.ev.normalize_schedule(sched)

        fallback = self._greedy_select(sched)
        fallback = self._fix_genre_runs(fallback)
        fallback = self._remove_duplicate_program_usage(fallback)
        fallback = self._greedy_select(fallback)

        if self.ev.evaluate(fallback)["feasible"]:
            return self.ev.normalize_schedule(fallback)

        return []


# ============================================================
# Genetic operators
# ============================================================

class GeneticOperators:
    def __init__(self, evaluator, pool, repair_engine, rng):
        self.ev = evaluator
        self.pool = pool
        self.repair_engine = repair_engine
        self.rng = rng

    def crossover_time_cut(self, p1, p2):
        p1 = self.ev.normalize_schedule(p1)
        p2 = self.ev.normalize_schedule(p2)

        if not p1 and not p2:
            return []

        cut_candidates = [self.ev.O, self.ev.E]
        for s in p1:
            cut_candidates.extend([s["seg_start"], s["seg_end"]])
        for s in p2:
            cut_candidates.extend([s["seg_start"], s["seg_end"]])

        cut = self.rng.choice(cut_candidates)

        left = [dict(s) for s in p1 if s["seg_end"] <= cut]
        right = [dict(s) for s in p2 if s["seg_start"] >= cut]

        child = left + right
        return self.repair_engine.repair(child)

    def crossover_block_mix(self, p1, p2):
        p1 = self.ev.normalize_schedule(p1)
        p2 = self.ev.normalize_schedule(p2)

        if not p1:
            return deep_copy_schedule(p2)
        if not p2:
            return deep_copy_schedule(p1)

        times = []
        for s in p1 + p2:
            times.extend([s["seg_start"], s["seg_end"]])
        times = sorted(set(times))

        if len(times) < 2:
            return self.crossover_time_cut(p1, p2)

        t1 = self.rng.choice(times[:-1])
        t2 = self.rng.choice([t for t in times if t > t1])

        middle = [dict(s) for s in p1 if interval_overlap_len(s["seg_start"], s["seg_end"], t1, t2) > 0]
        outside = [dict(s) for s in p2 if interval_overlap_len(s["seg_start"], s["seg_end"], t1, t2) == 0]

        child = outside + middle
        return self.repair_engine.repair(child)

    def mutate_replace_segment(self, schedule):
        child = self.ev.normalize_schedule(schedule)
        if not child:
            return []

        idx = self.rng.randrange(len(child))
        target = child[idx]

        alternatives = self.pool.alternatives_for_segment(target, slack=75, limit=100)
        if not self.ev.allow_program_revisit:
            used_programs = {s["program_id"] for j, s in enumerate(child) if j != idx}
            alternatives = [a for a in alternatives if a["program_id"] not in used_programs]

        alt = random_choice_or_none(alternatives, self.rng)
        if alt is None:
            return child

        child[idx] = dict(alt)
        return self.repair_engine.repair(child)

    def mutate_delete_weak(self, schedule):
        child = self.ev.normalize_schedule(schedule)
        if not child:
            return []

        scored = [(self.ev.marginal_contribution(child, i), i) for i in range(len(child))]
        scored.sort(key=lambda x: x[0])
        _, idx = scored[0]
        child.pop(idx)
        return self.repair_engine.repair(child)

    def mutate_insert_gap(self, schedule):
        child = self.ev.normalize_schedule(schedule)
        child.sort(key=lambda x: (x["seg_start"], x["seg_end"]))

        gaps = []
        cur = self.ev.O
        for s in child:
            if cur < s["seg_start"]:
                gaps.append((cur, s["seg_start"]))
            cur = max(cur, s["seg_end"])
        if cur < self.ev.E:
            gaps.append((cur, self.ev.E))

        gaps = [g for g in gaps if g[1] - g[0] >= self.ev.D]
        if not gaps:
            return child

        gs, ge = self.rng.choice(gaps)
        cands = self.pool.gap_candidates(gs, ge, limit=120)

        if not self.ev.allow_program_revisit:
            used_programs = {s["program_id"] for s in child}
            cands = [c for c in cands if c["program_id"] not in used_programs]

        if not cands:
            return child

        cand = self.rng.choice(cands[: min(12, len(cands))])
        child.append(dict(cand))
        return self.repair_engine.repair(child)

    def mutate_expand_boundary(self, schedule):
        child = self.ev.normalize_schedule(schedule)
        if not child:
            return []

        idxs = [
            i for i, s in enumerate(child)
            if s["seg_start"] > s["prog_start"] or s["seg_end"] < s["prog_end"]
        ]
        if not idxs:
            return child

        idx = self.rng.choice(idxs)
        seg = child[idx]

        alternatives = self.pool.by_program.get(seg["program_id"], [])
        better = []
        for a in alternatives:
            if a["channel_id"] != seg["channel_id"]:
                continue
            if a["seg_start"] <= seg["seg_start"] and a["seg_end"] >= seg["seg_end"]:
                if effective_duration(a) >= effective_duration(seg):
                    better.append(a)

        if not better:
            return child

        better.sort(key=lambda x: (-effective_duration(x), -seg_value(x)))
        child[idx] = dict(better[0])
        return self.repair_engine.repair(child)

    def mutate_block_rebuild(self, schedule):
        child = self.ev.normalize_schedule(schedule)
        if not child:
            return []

        if len(child) == 1:
            return self.mutate_insert_gap(child)

        i = self.rng.randrange(len(child))
        j = min(len(child), i + self.rng.randint(1, 3))

        left = child[:i]
        right = child[j:]

        block_start = left[-1]["seg_end"] if left else self.ev.O
        block_end = right[0]["seg_start"] if right else self.ev.E

        rebuilt = deep_copy_schedule(left + right)

        if block_end - block_start >= self.ev.D:
            cands = self.pool.gap_candidates(block_start, block_end, limit=120)

            if not self.ev.allow_program_revisit:
                used_programs = {s["program_id"] for s in rebuilt}
                cands = [c for c in cands if c["program_id"] not in used_programs]

            self.rng.shuffle(cands)
            for cand in cands[:15]:
                rebuilt.append(dict(cand))

        return self.repair_engine.repair(rebuilt)

    def mutate_channel_continuation(self, schedule):
        child = self.ev.normalize_schedule(schedule)
        if len(child) < 2:
            return child

        idx = self.rng.randrange(1, len(child))
        prev_seg = child[idx - 1]
        next_seg = child[idx + 1] if idx + 1 < len(child) else None
        old_seg = child[idx]

        cands = self.pool.channel_continuation_candidates(prev_seg, next_seg=next_seg, limit=80)
        if not cands:
            return child

        if not self.ev.allow_program_revisit:
            used = {s["program_id"] for j, s in enumerate(child) if j != idx}
            cands = [c for c in cands if c["program_id"] not in used]

        if not cands:
            return child

        current_value = seg_value(old_seg)
        cands.sort(key=lambda x: (-seg_value(x), x["seg_start"], x["seg_end"]))

        # Prefer high value same-channel continuation, but allow neutral alternatives
        for cand in cands[:12]:
            if seg_value(cand) >= current_value - self.ev.S:
                child[idx] = dict(cand)
                return self.repair_engine.repair(child)

        return child

    def mutate(self, schedule):
        ops = [
            self.mutate_replace_segment,
            self.mutate_delete_weak,
            self.mutate_insert_gap,
            self.mutate_expand_boundary,
            self.mutate_block_rebuild,
            self.mutate_channel_continuation,
        ]
        op = self.rng.choice(ops)
        return op(schedule)


# ============================================================
# Advanced Local Search
# ============================================================

class AdvancedLocalSearch:
    """
    Intensification phase applied after GA.

    It searches around the best GA solution using several neighborhoods:
    - best replacement of weak or random segments
    - insertion into useful gaps
    - expansion of partial broadcasts
    - deletion of harmful weak segments
    - block rebuild around local schedule windows
    - channel-continuation moves to reduce switch penalties

    Only improving moves are accepted. This protects solution quality while
    allowing fine-grained improvement after the global GA exploration.
    """

    def __init__(
        self,
        evaluator,
        pool,
        repair_engine,
        operators,
        rng,
        max_iterations=80,
        candidates_per_iteration=14,
        no_improve_limit=18,
        replacement_limit=35,
        gap_limit=80,
    ):
        self.ev = evaluator
        self.pool = pool
        self.repair_engine = repair_engine
        self.ops = operators
        self.rng = rng
        self.max_iterations = max_iterations
        self.candidates_per_iteration = candidates_per_iteration
        self.no_improve_limit = no_improve_limit
        self.replacement_limit = replacement_limit
        self.gap_limit = gap_limit

    def _score(self, schedule):
        schedule = self.ev.normalize_schedule(schedule)
        evaluation = self.ev.evaluate(schedule)
        return schedule, evaluation

    def _accept_if_better(self, base_eval, candidate):
        candidate = self.repair_engine.repair(candidate)
        candidate = self.ev.normalize_schedule(candidate)
        candidate_eval = self.ev.evaluate(candidate)

        if not candidate_eval["feasible"]:
            return None, None

        if candidate_eval["score"] > base_eval["score"]:
            return candidate, candidate_eval

        return None, None

    def _candidate_replace_moves(self, schedule, base_eval):
        moves = []
        sched = self.ev.normalize_schedule(schedule)
        if not sched:
            return moves

        # Try weak segments first because they are more likely to be replaceable.
        scored = []
        for i in range(len(sched)):
            scored.append((self.ev.marginal_contribution(sched, i), i))
        scored.sort(key=lambda x: x[0])

        candidate_indices = [i for _, i in scored[: min(5, len(scored))]]
        while len(candidate_indices) < min(8, len(sched)):
            idx = self.rng.randrange(len(sched))
            if idx not in candidate_indices:
                candidate_indices.append(idx)

        for idx in candidate_indices:
            target = sched[idx]
            alternatives = self.pool.alternatives_for_segment(
                target,
                slack=90,
                limit=self.replacement_limit,
            )

            if not self.ev.allow_program_revisit:
                used = {s["program_id"] for j, s in enumerate(sched) if j != idx}
                alternatives = [a for a in alternatives if a["program_id"] not in used]

            for alt in alternatives[: self.replacement_limit]:
                trial = deep_copy_schedule(sched)
                trial[idx] = dict(alt)
                improved, ev = self._accept_if_better(base_eval, trial)
                if improved is not None:
                    moves.append((improved, ev, "replace_segment"))

        return moves

    def _candidate_gap_insert_moves(self, schedule, base_eval):
        moves = []
        sched = self.ev.normalize_schedule(schedule)
        sched.sort(key=lambda x: (x["seg_start"], x["seg_end"]))

        gaps = []
        cur = self.ev.O
        for s in sched:
            if cur < s["seg_start"]:
                gaps.append((cur, s["seg_start"]))
            cur = max(cur, s["seg_end"])
        if cur < self.ev.E:
            gaps.append((cur, self.ev.E))

        useful_gaps = [g for g in gaps if g[1] - g[0] >= self.ev.D]
        useful_gaps.sort(key=lambda g: -(g[1] - g[0]))

        for gs, ge in useful_gaps[:8]:
            cands = self.pool.gap_candidates(gs, ge, limit=self.gap_limit)
            if not self.ev.allow_program_revisit:
                used = {s["program_id"] for s in sched}
                cands = [c for c in cands if c["program_id"] not in used]

            for cand in cands[: min(18, len(cands))]:
                trial = deep_copy_schedule(sched)
                trial.append(dict(cand))
                improved, ev = self._accept_if_better(base_eval, trial)
                if improved is not None:
                    moves.append((improved, ev, "insert_gap"))

        return moves

    def _candidate_expand_moves(self, schedule, base_eval):
        moves = []
        sched = self.ev.normalize_schedule(schedule)

        partial_indices = [
            i for i, s in enumerate(sched)
            if s["seg_start"] > s["prog_start"] or s["seg_end"] < s["prog_end"]
        ]

        self.rng.shuffle(partial_indices)
        for idx in partial_indices[:12]:
            seg = sched[idx]
            alternatives = self.pool.by_program.get(seg["program_id"], [])

            expanded = []
            for a in alternatives:
                if a["channel_id"] != seg["channel_id"]:
                    continue
                if a["seg_start"] <= seg["seg_start"] and a["seg_end"] >= seg["seg_end"]:
                    if effective_duration(a) > effective_duration(seg):
                        expanded.append(a)

            expanded.sort(key=lambda x: (-effective_duration(x), -seg_value(x)))

            for alt in expanded[:10]:
                trial = deep_copy_schedule(sched)
                trial[idx] = dict(alt)
                improved, ev = self._accept_if_better(base_eval, trial)
                if improved is not None:
                    moves.append((improved, ev, "expand_partial"))

        return moves

    def _candidate_delete_moves(self, schedule, base_eval):
        moves = []
        sched = self.ev.normalize_schedule(schedule)
        if len(sched) <= 1:
            return moves

        scored = [(self.ev.marginal_contribution(sched, i), i) for i in range(len(sched))]
        scored.sort(key=lambda x: x[0])

        # If marginal contribution is negative or very low, deletion may improve score
        for _, idx in scored[: min(10, len(scored))]:
            trial = deep_copy_schedule(sched)
            trial.pop(idx)
            improved, ev = self._accept_if_better(base_eval, trial)
            if improved is not None:
                moves.append((improved, ev, "delete_weak"))

        return moves

    def _candidate_block_rebuild_moves(self, schedule, base_eval):
        moves = []
        sched = self.ev.normalize_schedule(schedule)
        if len(sched) < 2:
            return moves

        attempts = min(self.candidates_per_iteration, max(4, len(sched) // 10))
        for _ in range(attempts):
            i = self.rng.randrange(len(sched))
            block_size = self.rng.randint(1, 4)
            j = min(len(sched), i + block_size)

            left = sched[:i]
            right = sched[j:]
            block_start = left[-1]["seg_end"] if left else self.ev.O
            block_end = right[0]["seg_start"] if right else self.ev.E

            if block_end - block_start < self.ev.D:
                continue

            rebuilt = deep_copy_schedule(left + right)
            cands = self.pool.gap_candidates(block_start, block_end, limit=self.gap_limit)

            if not self.ev.allow_program_revisit:
                used = {s["program_id"] for s in rebuilt}
                cands = [c for c in cands if c["program_id"] not in used]

            # Try greedy high-value rebuild and several randomized rebuilds.
            trial = deep_copy_schedule(rebuilt)
            for cand in cands[:12]:
                trial.append(dict(cand))
            improved, ev = self._accept_if_better(base_eval, trial)
            if improved is not None:
                moves.append((improved, ev, "block_rebuild_greedy"))

            for _rnd in range(3):
                trial = deep_copy_schedule(rebuilt)
                cands_copy = list(cands[:30])
                self.rng.shuffle(cands_copy)
                for cand in cands_copy[:10]:
                    trial.append(dict(cand))
                improved, ev = self._accept_if_better(base_eval, trial)
                if improved is not None:
                    moves.append((improved, ev, "block_rebuild_random"))

        return moves

    def _candidate_channel_continuation_moves(self, schedule, base_eval):
        moves = []
        sched = self.ev.normalize_schedule(schedule)
        if len(sched) < 2:
            return moves

        switch_indices = [
            i for i in range(1, len(sched))
            if sched[i - 1]["channel_id"] != sched[i]["channel_id"]
        ]

        self.rng.shuffle(switch_indices)

        for idx in switch_indices[:12]:
            prev_seg = sched[idx - 1]
            next_seg = sched[idx + 1] if idx + 1 < len(sched) else None
            cands = self.pool.channel_continuation_candidates(prev_seg, next_seg=next_seg, limit=50)

            if not self.ev.allow_program_revisit:
                used = {s["program_id"] for j, s in enumerate(sched) if j != idx}
                cands = [c for c in cands if c["program_id"] not in used]

            for cand in cands[:10]:
                trial = deep_copy_schedule(sched)
                trial[idx] = dict(cand)
                improved, ev = self._accept_if_better(base_eval, trial)
                if improved is not None:
                    moves.append((improved, ev, "channel_continuation"))

        return moves

    def improve(self, schedule, time_limit_seconds=None):
        start = time.time()

        best = self.repair_engine.repair(schedule)
        best = self.ev.normalize_schedule(best)
        best_eval = self.ev.evaluate(best)

        initial_score = best_eval["score"]
        improvements = 0
        iterations = 0
        no_improve = 0
        move_counts = defaultdict(int)

        if not best_eval["feasible"]:
            return best, best_eval, {
                "local_search_used": True,
                "local_search_initial_score": int(initial_score),
                "local_search_final_score": int(best_eval["score"]),
                "local_search_gain": 0,
                "local_search_iterations": 0,
                "local_search_improvements": 0,
                "local_search_runtime_seconds": 0.0,
                "local_search_move_counts": {},
            }

        while iterations < self.max_iterations:
            if time_limit_seconds is not None and time.time() - start >= time_limit_seconds:
                break

            iterations += 1
            base_eval = dict(best_eval)

            candidate_moves = []

            # Mixed deterministic/stochastic neighborhood scan.
            neighborhoods = [
                self._candidate_replace_moves,
                self._candidate_gap_insert_moves,
                self._candidate_expand_moves,
                self._candidate_delete_moves,
                self._candidate_block_rebuild_moves,
                self._candidate_channel_continuation_moves,
            ]
            self.rng.shuffle(neighborhoods)

            for neighborhood in neighborhoods:
                if time_limit_seconds is not None and time.time() - start >= time_limit_seconds:
                    break
                candidate_moves.extend(neighborhood(best, base_eval))

                # Avoid too much work on huge schedules.
                if len(candidate_moves) >= self.candidates_per_iteration:
                    break

            if not candidate_moves:
                no_improve += 1
                if no_improve >= self.no_improve_limit:
                    break
                continue

            candidate_moves.sort(key=lambda x: x[1]["score"], reverse=True)
            best_candidate, best_candidate_eval, move_name = candidate_moves[0]

            if best_candidate_eval["score"] > best_eval["score"]:
                best = deep_copy_schedule(best_candidate)
                best_eval = dict(best_candidate_eval)
                improvements += 1
                move_counts[move_name] += 1
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= self.no_improve_limit:
                    break

        runtime = time.time() - start
        stats = {
            "local_search_used": True,
            "local_search_initial_score": int(initial_score),
            "local_search_final_score": int(best_eval["score"]),
            "local_search_gain": int(best_eval["score"] - initial_score),
            "local_search_iterations": iterations,
            "local_search_improvements": improvements,
            "local_search_runtime_seconds": round(runtime, 4),
            "local_search_move_counts": dict(move_counts),
        }

        return self.ev.normalize_schedule(best), best_eval, stats


# ============================================================
# Hybrid GA engine
# ============================================================

class HybridGAScheduler:
    def __init__(
        self,
        data,
        segments,
        deterministic_seed,
        population_size=24,
        elite_count=2,
        crossover_rate=0.85,
        mutation_rate=0.35,
        seed=42,
        allow_program_revisit=False,
        revisit_penalty=25,
        use_local_search=True,
        local_search_iterations=80,
        local_search_candidates=14,
        local_search_no_improve=18,
        local_search_time_ratio=0.20,
        local_search_max_seconds=15.0,
    ):
        self.data = data
        self.rng = random.Random(seed)

        self.ev = Evaluator(
            data,
            allow_program_revisit=allow_program_revisit,
            revisit_penalty=revisit_penalty,
        )
        self.pool = CandidatePool(segments)
        self.repair_engine = RepairEngine(self.ev, self.pool)
        self.ops = GeneticOperators(self.ev, self.pool, self.repair_engine, self.rng)

        self.population_size = population_size
        self.elite_count = elite_count
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate

        self.use_local_search = use_local_search
        self.local_search_iterations = local_search_iterations
        self.local_search_candidates = local_search_candidates
        self.local_search_no_improve = local_search_no_improve
        self.local_search_time_ratio = local_search_time_ratio
        self.local_search_max_seconds = local_search_max_seconds

        self.local_search = AdvancedLocalSearch(
            evaluator=self.ev,
            pool=self.pool,
            repair_engine=self.repair_engine,
            operators=self.ops,
            rng=self.rng,
            max_iterations=self.local_search_iterations,
            candidates_per_iteration=self.local_search_candidates,
            no_improve_limit=self.local_search_no_improve,
        )

        self.deterministic_seed = self.repair_engine.repair(deterministic_seed)
        self.cache = {}

    def score(self, schedule):
        normalized = self.ev.normalize_schedule(schedule)
        key = schedule_key(normalized)
        if key not in self.cache:
            self.cache[key] = self.ev.evaluate(normalized)
        return self.cache[key]

    def tournament_select(self, population, k=3):
        sample = [population[self.rng.randrange(len(population))] for _ in range(k)]
        sample.sort(key=lambda x: self.score(x)["score"], reverse=True)
        return deep_copy_schedule(sample[0])

    def initialize_population(self):
        pop = []
        pop.append(deep_copy_schedule(self.deterministic_seed))

        while len(pop) < max(6, self.population_size // 3):
            child = deep_copy_schedule(self.deterministic_seed)
            n_mut = 1 + self.rng.randint(0, 2)
            for _ in range(n_mut):
                child = self.ops.mutate(child)
            child = self.repair_engine.repair(child)
            pop.append(child)

        while len(pop) < self.population_size:
            child = deep_copy_schedule(self.deterministic_seed)
            n_mut = 2 + self.rng.randint(1, 4)
            for _ in range(n_mut):
                child = self.ops.mutate(child)

            if self.rng.random() < 0.35:
                inject_n = self.rng.randint(1, 3)
                for _ in range(inject_n):
                    cand = random_choice_or_none(
                        self.pool.all_segments[: min(150, len(self.pool.all_segments))],
                        self.rng
                    )
                    if cand is not None:
                        child.append(dict(cand))
                child = self.repair_engine.repair(child)

            pop.append(child)

        unique = {}
        for ind in pop:
            norm = self.ev.normalize_schedule(ind)
            unique[schedule_key(norm)] = norm

        pop = list(unique.values())
        pop.sort(key=lambda x: self.score(x)["score"], reverse=True)

        while len(pop) < self.population_size:
            pop.append(deep_copy_schedule(pop[0]))

        return pop[: self.population_size]

    def evolve(self, time_limit_seconds=300):
        start = time.time()
        population = self.initialize_population()
        best = max(population, key=lambda x: self.score(x)["score"])
        best_score = self.score(best)["score"]

        generations_without_improvement = 0
        generations = 0

        while time.time() - start < time_limit_seconds:
            generations += 1
            population.sort(key=lambda x: self.score(x)["score"], reverse=True)
            new_population = [deep_copy_schedule(ind) for ind in population[: self.elite_count]]

            while len(new_population) < self.population_size and time.time() - start < time_limit_seconds:
                p1 = self.tournament_select(population)
                p2 = self.tournament_select(population)

                if self.rng.random() < self.crossover_rate:
                    if self.rng.random() < 0.55:
                        child = self.ops.crossover_time_cut(p1, p2)
                    else:
                        child = self.ops.crossover_block_mix(p1, p2)
                else:
                    child = deep_copy_schedule(
                        p1 if self.score(p1)["score"] >= self.score(p2)["score"] else p2
                    )

                if self.rng.random() < self.mutation_rate:
                    n_mut = 1 if self.rng.random() < 0.7 else 2
                    for _ in range(n_mut):
                        child = self.ops.mutate(child)

                child = self.repair_engine.repair(child)
                new_population.append(child)

            unique = {}
            for ind in new_population:
                norm = self.ev.normalize_schedule(ind)
                unique[schedule_key(norm)] = norm
            population = list(unique.values())

            population.sort(key=lambda x: self.score(x)["score"], reverse=True)
            if len(population) > self.population_size:
                population = population[: self.population_size]

            while len(population) < self.population_size:
                fallback = deep_copy_schedule(best)
                fallback = self.ops.mutate(fallback)
                fallback = self.repair_engine.repair(fallback)
                population.append(fallback)

            current_best = population[0]
            current_score = self.score(current_best)["score"]

            if current_score > best_score:
                best = deep_copy_schedule(current_best)
                best_score = current_score
                generations_without_improvement = 0
            else:
                generations_without_improvement += 1

            if generations_without_improvement >= 30:
                for i in range(max(1, self.population_size // 3), self.population_size):
                    mutated = deep_copy_schedule(best)
                    for _ in range(2 + self.rng.randint(0, 2)):
                        mutated = self.ops.mutate(mutated)
                    mutated = self.repair_engine.repair(mutated)
                    population[i] = mutated
                generations_without_improvement = 0

        best = self.ev.normalize_schedule(best)
        best_eval = self.score(best)

        ls_stats = {
            "local_search_used": False,
            "local_search_initial_score": int(best_eval["score"]),
            "local_search_final_score": int(best_eval["score"]),
            "local_search_gain": 0,
            "local_search_iterations": 0,
            "local_search_improvements": 0,
            "local_search_runtime_seconds": 0.0,
            "local_search_move_counts": {},
        }

        if self.use_local_search:
            local_time_limit = max(
                1.0,
                min(self.local_search_max_seconds, time_limit_seconds * self.local_search_time_ratio),
            )
            improved, improved_eval, ls_stats = self.local_search.improve(
                best,
                time_limit_seconds=local_time_limit,
            )
            if improved_eval["feasible"] and improved_eval["score"] >= best_eval["score"]:
                best = improved
                best_eval = improved_eval

        ga_stats = {
            "ga_generations": generations,
            "ga_best_score_before_local_search": int(best_score),
        }

        return best, best_eval, ga_stats, ls_stats


# ============================================================
# Orchestration
# ============================================================

def run_one_ga(
    data,
    top_k=8,
    population_size=24,
    elite_count=2,
    crossover_rate=0.85,
    mutation_rate=0.35,
    time_limit=300,
    seed=42,
    allow_program_revisit=False,
    revisit_penalty=25,
    deterministic_max_iters=40,
    use_local_search=True,
    local_search_iterations=80,
    local_search_candidates=14,
    local_search_no_improve=18,
    local_search_time_ratio=0.20,
    local_search_max_seconds=15.0,
):
    total_start = time.time()

    segments = build_segments(data)
    if not segments:
        return {
            "scheduled_programs": [],
            "total_score": 0,
            "meta": {
                "seed": seed,
                "feasible": True,
                "population_size": population_size,
                "elite_count": elite_count,
                "crossover_rate": crossover_rate,
                "mutation_rate": mutation_rate,
                "top_k_segments_per_program": top_k,
                "time_limit_seconds": time_limit,
                "runtime_seconds": 0.0,
                "deterministic_seed_score": 0,
                "ga_score": 0,
                "switches": 0,
                "partials": 0,
                "bonus": 0,
                "program_score": 0,
                "revisits": 0,
                "normalized_length": 0,
                "allow_program_revisit": allow_program_revisit,
                "revisit_penalty": revisit_penalty,
                "local_search_used": False,
                "local_search_gain": 0,
            },
        }

    segments = keep_top_k_per_program(segments, top_k=top_k)

    deterministic_schedule, deterministic_score = improve_unique_programs(
        segments,
        R=data["max_consecutive_genre"],
        S=data["switch_penalty"],
        max_iters=deterministic_max_iters,
    )

    ga_start = time.time()

    ga = HybridGAScheduler(
        data=data,
        segments=segments,
        deterministic_seed=deterministic_schedule,
        population_size=population_size,
        elite_count=elite_count,
        crossover_rate=crossover_rate,
        mutation_rate=mutation_rate,
        seed=seed,
        allow_program_revisit=allow_program_revisit,
        revisit_penalty=revisit_penalty,
        use_local_search=use_local_search,
        local_search_iterations=local_search_iterations,
        local_search_candidates=local_search_candidates,
        local_search_no_improve=local_search_no_improve,
        local_search_time_ratio=local_search_time_ratio,
        local_search_max_seconds=local_search_max_seconds,
    )

    best_schedule, best_eval, ga_stats, local_search_stats = ga.evolve(time_limit_seconds=time_limit)
    ga_runtime = time.time() - ga_start
    total_runtime = time.time() - total_start

    normalized_best = ga.ev.normalize_schedule(best_schedule)

    return {
        "scheduled_programs": [
            {
                "program_id": s["program_id"],
                "channel_id": s["channel_id"],
                "start": s["seg_start"],
                "end": s["seg_end"],
            }
            for s in normalized_best
        ],
        "total_score": int(best_eval["score"]),
        "meta": {
            "seed": seed,
            "feasible": best_eval["feasible"],
            "population_size": population_size,
            "elite_count": elite_count,
            "crossover_rate": crossover_rate,
            "mutation_rate": mutation_rate,
            "time_limit_seconds": time_limit,
            "ga_runtime_seconds": round(ga_runtime, 4),
            "runtime_seconds": round(total_runtime, 4),
            "deterministic_seed_score": int(deterministic_score),
            "ga_score": int(best_eval["score"]),
            "switches": int(best_eval["switches"]),
            "partials": int(best_eval["partials"]),
            "bonus": int(best_eval["bonus"]),
            "program_score": int(best_eval["program_score"]),
            "revisits": int(best_eval["revisits"]),
            "normalized_length": int(best_eval["normalized_length"]),
            "top_k_segments_per_program": top_k,
            "allow_program_revisit": allow_program_revisit,
            "revisit_penalty": revisit_penalty,
            "deterministic_max_iters": deterministic_max_iters,
            **ga_stats,
            **local_search_stats,
        },
    }


def run_multi(
    data,
    runs=10,
    time_limit=300,
    top_k=8,
    population_size=24,
    elite_count=2,
    crossover_rate=0.85,
    mutation_rate=0.35,
    base_seed=42,
    allow_program_revisit=False,
    revisit_penalty=25,
    deterministic_max_iters=40,
    use_local_search=True,
    local_search_iterations=80,
    local_search_candidates=14,
    local_search_no_improve=18,
    local_search_time_ratio=0.20,
    local_search_max_seconds=15.0,
):
    all_runs = []
    best_result = None
    best_score = NEG_INF

    for run_idx in range(runs):
        seed = base_seed + 1009 * run_idx
        result = run_one_ga(
            data=data,
            top_k=top_k,
            population_size=population_size,
            elite_count=elite_count,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            time_limit=time_limit,
            seed=seed,
            allow_program_revisit=allow_program_revisit,
            revisit_penalty=revisit_penalty,
            deterministic_max_iters=deterministic_max_iters,
            use_local_search=use_local_search,
            local_search_iterations=local_search_iterations,
            local_search_candidates=local_search_candidates,
            local_search_no_improve=local_search_no_improve,
            local_search_time_ratio=local_search_time_ratio,
            local_search_max_seconds=local_search_max_seconds,
        )
        all_runs.append(result)

        if result["total_score"] > best_score:
            best_score = result["total_score"]
            best_result = result

    scores = [r["total_score"] for r in all_runs]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    variance = sum((x - avg_score) ** 2 for x in scores) / len(scores) if scores else 0.0
    std_dev = math.sqrt(variance)

    best_result["experiment"] = {
        "runs": runs,
        "best_score": int(max(scores) if scores else 0),
        "average_score": round(avg_score, 4),
        "std_dev": round(std_dev, 4),
        "scores": scores,
        "top_k": top_k,
        "population_size": population_size,
        "elite_count": elite_count,
        "crossover_rate": crossover_rate,
        "mutation_rate": mutation_rate,
        "use_local_search": use_local_search,
        "local_search_iterations": local_search_iterations,
        "local_search_candidates": local_search_candidates,
        "local_search_no_improve": local_search_no_improve,
    }

    return best_result, all_runs


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Hybrid GA + Advanced Local Search smart TV scheduler")
    parser.add_argument("input_json", help="Path to instance json")
    parser.add_argument("output_json", help="Path to output json")
    parser.add_argument("--runs", type=int, default=10, help="Number of independent GA runs")
    parser.add_argument("--time-limit", type=int, default=300, help="Time limit per run in seconds")
    parser.add_argument("--population", type=int, default=24, help="Population size")
    parser.add_argument("--elite", type=int, default=2, help="Elite count")
    parser.add_argument("--top-k", type=int, default=8, help="Top K segments kept per program")
    parser.add_argument("--crossover-rate", type=float, default=0.85, help="Crossover probability")
    parser.add_argument("--mutation-rate", type=float, default=0.35, help="Mutation probability")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    parser.add_argument("--allow-program-revisit", action="store_true", help="Allow the same program to reappear later")
    parser.add_argument("--revisit-penalty", type=int, default=25, help="Penalty for revisiting a program")
    parser.add_argument("--deterministic-max-iters", type=int, default=40, help="Max iterations for deterministic seed improvement")
    parser.add_argument("--no-local-search", action="store_true", help="Disable advanced local search phase")
    parser.add_argument("--local-search-iterations", type=int, default=80, help="Maximum local search iterations")
    parser.add_argument("--local-search-candidates", type=int, default=14, help="Candidate moves checked per local search iteration")
    parser.add_argument("--local-search-no-improve", type=int, default=18, help="Stop local search after N iterations without improvement")
    parser.add_argument("--local-search-time-ratio", type=float, default=0.20, help="Local search time as ratio of GA time limit")
    parser.add_argument("--local-search-max-seconds", type=float, default=15.0, help="Maximum seconds used by local search")
    parser.add_argument("--dump-all-runs", default=None, help="Optional json path to store all runs")
    args = parser.parse_args()

    with open(args.input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    best_result, all_runs = run_multi(
        data=data,
        runs=args.runs,
        time_limit=args.time_limit,
        top_k=args.top_k,
        population_size=args.population,
        elite_count=args.elite,
        crossover_rate=args.crossover_rate,
        mutation_rate=args.mutation_rate,
        base_seed=args.seed,
        allow_program_revisit=args.allow_program_revisit,
        revisit_penalty=args.revisit_penalty,
        deterministic_max_iters=args.deterministic_max_iters,
        use_local_search=not args.no_local_search,
        local_search_iterations=args.local_search_iterations,
        local_search_candidates=args.local_search_candidates,
        local_search_no_improve=args.local_search_no_improve,
        local_search_time_ratio=args.local_search_time_ratio,
        local_search_max_seconds=args.local_search_max_seconds,
    )

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(best_result, f, indent=2)

    if args.dump_all_runs:
        with open(args.dump_all_runs, "w", encoding="utf-8") as f:
            json.dump(all_runs, f, indent=2)

    print("Best solution written to:", args.output_json)
    print("Best score:", best_result["total_score"])
    print("Experiment stats:", best_result.get("experiment", {}))
    print("Meta:", best_result.get("meta", {}))


if __name__ == "__main__":
    main()
