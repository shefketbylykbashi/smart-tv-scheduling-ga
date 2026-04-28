# Smart TV Scheduling with Segment-Based Deterministic Scheduling (SBDS)

This repository provides an implementation of a deterministic optimization method for the TV Channel Scheduling problem in public environments. The goal is to construct a continuous broadcast schedule that maximizes content utility while respecting operational constraints such as temporal feasibility, genre diversity, switching penalties, and priority blocks.

The approach departs from traditional program-level formulations by introducing a segment-based representation of candidate decisions. Instead of selecting entire programs, the method constructs feasible sub-intervals aligned with temporal constraints and preference structures. This allows the scheduler to exploit fine-grained opportunities in dense broadcast environments where strict program-level decisions may be overly restrictive.

The core optimization is performed using a dynamic programming procedure defined over temporally ordered segments. Each state captures both the accumulated score and the current genre continuity, enabling direct enforcement of diversity constraints. To maintain computational tractability, only the top-ranked candidate segments per program are retained, which preserves solution quality while reducing the search space.

A distinguishing aspect of the implementation is the deterministic repair phase applied after each optimization pass. Since segment-based modeling may produce multiple selections from the same original program, a structured elimination process removes weaker occurrences and re-solves the problem. This iterative refinement continues until a consistent schedule is obtained, where each program appears at most once.

The repository includes a collection of benchmark instances covering different scheduling scenarios, including traditional TV channels, IPTV streams, provider-based schedules, and YouTube live content. These instances are used to evaluate the behavior of the method under varying levels of density, overlap, and structural constraints.

The reported results correspond to the deterministic scheduler applied to each instance. The method demonstrates strong performance in large-scale scenarios, particularly where temporal flexibility and segment alignment play a significant role in the achievable score.

---

## Algorithm Overview

The method follows a structured pipeline in which candidate segments are first generated and filtered, after which a dynamic programming procedure constructs a schedule subject to all constraints. A deterministic repair phase is then applied to ensure that each program appears at most once.

### Pseudocode

```text
Input: instance data
Output: schedule S

1. segments ← generate_segments(instance)
2. segments ← keep_top_K_per_program(segments, K)

3. repeat
4.     S ← DP_optimize(segments)
5.     duplicates ← find_program_duplicates(S)

6.     if duplicates is empty then
7.         return S
8.     end if

9.     for each program p in duplicates do
10.        keep best occurrence of p in S
11.        remove weaker occurrences from segments
12.    end for

13. until no duplicates or iteration limit reached
```

### Dynamic Programming Core

```text
Input: segments sorted by start time
Output: best feasible schedule

for each segment i:
    initialize DP[i][1] with segment value

for each segment i in temporal order:
    for each compatible predecessor j:
        if genre changes:
            update DP[i][1]
        if genre continues and limit not exceeded:
            update DP[i][k+1]

return best scoring state and reconstruct schedule
```

The dynamic programming phase is exact with respect to the retained segment set. The full method is not globally exact, since candidate generation and top-$K$ pruning restrict the explored search space.

---

## Repository Structure

```text
smart-tv-scheduling-sbds/
├── src/
│   └── smart_tv_scheduler_scoreboost.py
├── instances/
├── results/
├── tables/
│   └── results_summary.csv
├── scripts/
│   └── run_all_instances.py
├── README.md
├── CITATION.cff
├── LICENSE
├── requirements.txt
```

The `src/` directory contains the main implementation of the deterministic scheduler. The `instances/` directory stores the benchmark datasets, while `results/` contains the generated schedules. Summary tables used in the experimental section are located under `tables/`. Batch execution scripts are provided in `scripts/`.

---

## Running the Scheduler

To execute the scheduler on a single instance:

```bash
python src/smart_tv_scheduler_scoreboost.py instances/australia_iptv.json results/australia_iptv_output.json
```

To run all benchmark instances:

```bash
python scripts/run_all_instances.py
```

The implementation is fully deterministic. For a fixed input instance and identical configuration, repeated executions produce identical schedules and scores.

---

## Input Format

Each instance is provided as a JSON file with the following structure:

* Global parameters: opening time, closing time, minimum duration, maximum consecutive genre, switching penalty, termination penalty
* Priority blocks defining channel restrictions over time intervals
* Time preference windows associated with genre-based bonuses
* A set of channels, each containing a sequence of programs with start time, end time, genre, and score

The scheduler internally transforms these programs into candidate segments that satisfy all feasibility constraints.

---

## Output Format

The output is a JSON file containing:

* `scheduled_programs`: list of selected segments with program ID, channel, start, and end time
* `total_score`: aggregated score after accounting for bonuses and penalties

---

## Benchmark Instances

The repository includes the following instances:

* australia_iptv
* canada_pw
* china_pw
* croatia_tv
* france_iptv
* germany_tv
* kosovo_tv
* netherlands_tv
* singapore_pw
* spain_iptv
* uk_iptv
* uk_tv
* us_iptv
* usa_tv
* youtube_gold
* youtube_premium

These datasets reflect different scheduling conditions, ranging from sparse traditional programming to highly dense streaming environments.

---

## Reported Results

| Instance        |  Score |
| --------------- | -----: |
| australia_iptv  |   4883 |
| canada_pw       |   5663 |
| china_pw        |   3016 |
| croatia_tv      |   2220 |
| france_iptv     |  10983 |
| germany_tv      |   1481 |
| kosovo_tv       |   2572 |
| netherlands_tv  |   2584 |
| singapore_pw    |   6986 |
| spain_iptv      |   6655 |
| uk_iptv         |   9948 |
| uk_tv           |   2266 |
| us_iptv         |   5560 |
| usa_tv          |   3579 |
| youtube_gold    | 107435 |
| youtube_premium |  67862 |

---

## Reproducibility

All experiments reported in the repository are reproducible using the provided instances and scripts. The deterministic nature of the algorithm ensures that results do not depend on random seeds or stochastic components.

---

## Citation

If this repository is used in academic work, please cite the associated paper and the software record provided in `CITATION.cff`.

---

## License

This project is released under the MIT License.
