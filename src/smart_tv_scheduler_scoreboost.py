import json
import sys
from collections import defaultdict

NEG_INF = -10**18

def interval_overlap_len(a1, a2, b1, b2):
    return max(0, min(a2, b2) - max(a1, b1))

def preprocess_priority_blocks(priority_blocks):
    for b in priority_blocks:
        b["allowed_set"] = set(b.get("allowed_channels", []))
    priority_blocks.sort(key=lambda x: (x["start"], x["end"]))

def channel_allowed(channel_id, start, end, priority_blocks):
    for block in priority_blocks:
        if block["end"] <= start:
            continue
        if block["start"] >= end:
            break
        if channel_id not in block["allowed_set"]:
            return False
    return True

def compute_bonus(seg_start, seg_end, genre, D, time_prefs):
    total = 0
    for pref in time_prefs:
        if genre != pref["preferred_genre"]:
            continue
        if interval_overlap_len(seg_start, seg_end, pref["start"], pref["end"]) >= D:
            total += pref["bonus"]
    return total

def top2_init():
    return [(NEG_INF, None, None, None, None), (NEG_INF, None, None, None, None)]

def better(a, b):
    if a[0] != b[0]:
        return a[0] > b[0]
    ai = a[3] if a[3] is not None else 10**18
    bi = b[3] if b[3] is not None else 10**18
    return ai < bi

def top2_update(cur, cand):
    a, b = cur[0], cur[1]
    if not better(cand, b):
        return cur
    if better(cand, a):
        return [cand, a]
    return [a, cand]

def best_excluding_genre(top2_list, bad_genre):
    a, b = top2_list[0], top2_list[1]
    if a[0] > NEG_INF/2 and a[1] != bad_genre:
        return a
    if b[0] > NEG_INF/2 and b[1] != bad_genre:
        return b
    return (NEG_INF, None, None, None, None)

def best_matching_genre(top2_list, want_genre):
    a, b = top2_list[0], top2_list[1]
    if a[0] > NEG_INF/2 and a[1] == want_genre:
        return a
    if b[0] > NEG_INF/2 and b[1] == want_genre:
        return b
    return (NEG_INF, None, None, None, None)

def solve_dp(segments, R, S):
    M = len(segments)
    if M == 0:
        return [], 0

    segments = sorted(segments, key=lambda x: (x["seg_start"], x["seg_end"], x["channel_id"], x["program_id"]))
    by_end = sorted(range(M), key=lambda i: segments[i]["seg_end"])

    seg_value = [s["score"] + s["bonus"] - s["cut_penalty"] for s in segments]

    dp = [defaultdict(lambda: NEG_INF) for _ in range(M)]
    parent = {}

    # ended-structures
    global_best = [top2_init() for _ in range(R + 1)]
    global_best_anyk = top2_init()

    per_channel_best = [defaultdict(top2_init) for _ in range(R + 1)]
    per_channel_best_anyk = defaultdict(top2_init)

    for i in range(M):
        dp[i][1] = seg_value[i]
        parent[(i, 1)] = None

    end_ptr = 0

    for i in range(M):
        si = segments[i]
        start_i = si["seg_start"]
        g_i = si["genre"]
        ch_i = si["channel_id"]

        while end_ptr < M:
            j = by_end[end_ptr]
            if segments[j]["seg_end"] > start_i:
                break

            sj = segments[j]
            for k_prev, val_prev in dp[j].items():
                if val_prev <= NEG_INF/2:
                    continue
                cand = (val_prev, sj["genre"], sj["channel_id"], j, k_prev)

                global_best[k_prev] = top2_update(global_best[k_prev], cand)
                per_channel_best[k_prev][sj["channel_id"]] = top2_update(per_channel_best[k_prev][sj["channel_id"]], cand)

                global_best_anyk = top2_update(global_best_anyk, cand)
                per_channel_best_anyk[sj["channel_id"]] = top2_update(per_channel_best_anyk[sj["channel_id"]], cand)

            end_ptr += 1

        best_same_ch = best_excluding_genre(per_channel_best_anyk[ch_i], g_i)
        best_same_score = best_same_ch[0]

        best_global = best_excluding_genre(global_best_anyk, g_i)
        best_global_score = best_global[0] - S if best_global[0] > NEG_INF/2 else NEG_INF

        if best_same_score > NEG_INF/2 or best_global_score > NEG_INF/2:
            if best_same_score >= best_global_score:
                pred = best_same_ch
                pred_score = best_same_score
            else:
                pred = best_global
                pred_score = best_global_score

            cand_score = pred_score + seg_value[i]
            if cand_score > dp[i][1]:
                dp[i][1] = cand_score
                parent[(i, 1)] = (pred[3], pred[4])

        for k_prev in range(1, R):
            k_new = k_prev + 1

            best_same = best_matching_genre(per_channel_best[k_prev][ch_i], g_i)
            same_score = best_same[0]

            best_glob = best_matching_genre(global_best[k_prev], g_i)
            diff_score = best_glob[0] - S if best_glob[0] > NEG_INF/2 else NEG_INF

            if same_score <= NEG_INF/2 and diff_score <= NEG_INF/2:
                continue

            if same_score >= diff_score:
                pred = best_same
                pred_score = same_score
            else:
                pred = best_glob
                pred_score = diff_score

            cand_score = pred_score + seg_value[i]
            if cand_score > dp[i][k_new]:
                dp[i][k_new] = cand_score
                parent[(i, k_new)] = (pred[3], pred[4])

    best_score = NEG_INF
    best_state = None
    for i in range(M):
        for k, v in dp[i].items():
            if v > best_score:
                best_score = v
                best_state = (i, k)

    schedule_idx = []
    cur = best_state
    while cur is not None:
        i, k = cur
        schedule_idx.append(i)
        cur = parent.get(cur)
    schedule_idx.reverse()

    schedule = [segments[i] for i in schedule_idx]

    total = 0
    prev = None
    for s in schedule:
        total += s["score"] + s["bonus"] - s["cut_penalty"]
        if prev and prev["channel_id"] != s["channel_id"]:
            total -= S
        prev = s

    return schedule, total

def improve_unique_programs(all_segments, R, S, max_iters=15):
    disabled = set()

    def seg_key(s):
        return (s["program_id"], s["seg_start"], s["seg_end"], s["channel_id"])

    best_schedule = []
    best_score = NEG_INF

    for it in range(max_iters):
        active = [s for s in all_segments if seg_key(s) not in disabled]
        schedule, score = solve_dp(active, R, S)

        if score > best_score:
            best_score = score
            best_schedule = schedule

        occ = defaultdict(list)
        for idx, s in enumerate(schedule):
            occ[s["program_id"]].append((idx, s))

        dup_pids = [pid for pid, lst in occ.items() if len(lst) > 1]
        if not dup_pids:
            return schedule, score

        for pid in sorted(dup_pids):
            lst = occ[pid]

            def marginal(i, seg):
                base = seg["score"] + seg["bonus"] - seg["cut_penalty"]
                penalty = 0
                if i > 0 and schedule[i-1]["channel_id"] != seg["channel_id"]:
                    penalty += S
                if i < len(schedule)-1 and schedule[i+1]["channel_id"] != seg["channel_id"]:
                    penalty += S
                return base - penalty

            ranked = sorted(
                [(marginal(i, seg), i, seg) for (i, seg) in lst],
                key=lambda x: (-x[0], x[1], seg_key(x[2]))
            )

            keep = ranked[0][2]
            for _, _, seg in ranked[1:]:
                disabled.add(seg_key(seg))

    return best_schedule, best_score


def build_segments(data):
    O = data["opening_time"]
    E = data["closing_time"]
    D = data["min_duration"]
    T = data["termination_penalty"]

    priority_blocks = data.get("priority_blocks", [])
    time_prefs = data.get("time_preferences", [])

    preprocess_priority_blocks(priority_blocks)

    segments = []
    seen = set()

    interesting_times = set([O, E])
    for pref in time_prefs:
        interesting_times.add(pref["start"])
        interesting_times.add(pref["end"])
    for b in priority_blocks:
        interesting_times.add(b["start"])
        interesting_times.add(b["end"])
    interesting_times = sorted(t for t in interesting_times if O <= t <= E)

    def add_segment(base, seg_start, seg_end):
        if seg_start < O or seg_end > E or seg_end <= seg_start:
            return

        prog_len = base["end"] - base["start"]
        seg_len = seg_end - seg_start

        if prog_len < D:
            if seg_start != base["start"] or seg_end != base["end"]:
                return
        else:
            if seg_len < D:
                return

        if not channel_allowed(base["channel_id"], seg_start, seg_end, priority_blocks):
            return

        key = (base["program_id"], seg_start, seg_end, base["channel_id"])
        if key in seen:
            return
        seen.add(key)

        cut_penalty = 0
        if seg_start > base["start"]:
            cut_penalty += T
        if seg_end < base["end"]:
            cut_penalty += T

        bonus = compute_bonus(seg_start, seg_end, base["genre"], D, time_prefs)

        segments.append({
            "program_id": base["program_id"],
            "channel_id": base["channel_id"],
            "prog_start": base["start"],
            "prog_end": base["end"],
            "seg_start": seg_start,
            "seg_end": seg_end,
            "genre": base["genre"],
            "score": base["score"],
            "bonus": bonus,
            "cut_penalty": cut_penalty
        })

    for channel in data["channels"]:
        cid = channel["channel_id"]
        for p in channel["programs"]:
            if p["end"] <= O or p["start"] >= E:
                continue

            base = {
                "program_id": p["program_id"],
                "channel_id": cid,
                "start": max(p["start"], O),
                "end": min(p["end"], E),
                "genre": p["genre"],
                "score": p["score"]
            }

            full_start = max(p["start"], O)
            full_end = min(p["end"], E)

            add_segment(base, full_start, full_end)

            if full_end - full_start >= D:
                add_segment(base, full_start, full_start + D)
                add_segment(base, full_end - D, full_end)

            for pref in time_prefs:
                if p["genre"] != pref["preferred_genre"]:
                    continue
                s = max(full_start, pref["start"])
                e = s + D
                if e <= full_end:
                    add_segment(base, s, e)

            if full_end - full_start >= D:
                for t in interesting_times:
                    if full_start <= t <= full_end - D:
                        add_segment(base, t, t + D)
                    if full_start + D <= t <= full_end:
                        add_segment(base, t - D, t)

    return segments


def keep_top_k_per_program(segments, top_k=8):
    buckets = defaultdict(list)
    for s in segments:
        v = s["score"] + s["bonus"] - s["cut_penalty"]
        buckets[s["program_id"]].append((v, s))

    pruned = []
    for pid, lst in buckets.items():
        lst.sort(key=lambda x: (-x[0], x[1]["seg_start"], x[1]["seg_end"], x[1]["channel_id"]))
        for _, s in lst[:top_k]:
            pruned.append(s)

    return pruned

def main():
    if len(sys.argv) != 3:
        print("Usage: python smart_tv_scheduler_scoreboost.py input.json output.json")
        sys.exit(1)

    INPUT_FILE = sys.argv[1]
    OUTPUT_FILE = sys.argv[2]

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    O = data["opening_time"]
    E = data["closing_time"]
    D = data["min_duration"]
    R = data["max_consecutive_genre"]
    S = data["switch_penalty"]

    segments = build_segments(data)

    if not segments:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump({"scheduled_programs": [], "total_score": 0}, f, indent=2)
        print("✅ No valid segments.")
        return

    TOP_K = 8
    segments = keep_top_k_per_program(segments, top_k=TOP_K)

    schedule, final_score = improve_unique_programs(segments, R=R, S=S, max_iters=40)

    output = {
        "scheduled_programs": [
            {
                "program_id": s["program_id"],
                "channel_id": s["channel_id"],
                "start": s["seg_start"],
                "end": s["seg_end"]
            }
            for s in schedule
        ],
        "total_score": int(final_score)
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("Schedule written to", OUTPUT_FILE)
    print("Total score:", final_score)
    print(f"Segments kept per program: TOP_K={TOP_K}")
    print(f"Schedule length: {len(schedule)} programs")
    print(f"Window: [{O}..{E}), minDur={D}, R={R}, S={S}")

if __name__ == "__main__":
    main()
