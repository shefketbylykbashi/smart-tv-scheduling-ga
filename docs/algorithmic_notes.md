# Algorithmic Notes

These notes describe the deterministic dynamic-programming baseline implemented in `src/smart_tv_scheduler_scoreboost.py`. The GA and GA + local-search variants use this deterministic solver as their seed generator; their additional operators are summarized in `docs/methodology.md`.

## Problem Definition

The TV Channel Scheduling problem considered in this repository consists of selecting and ordering content from multiple channels over a fixed time horizon. Each channel provides a sequence of programs defined by start time, end time, genre, and a base score. The goal is to construct a valid broadcast schedule that maximizes total utility.

A feasible schedule must satisfy several constraints: programs must lie within the operating horizon, no overlaps are allowed, each selected segment must respect a minimum duration, and the sequence must not exceed a predefined number of consecutive programs of the same genre. Additional constraints arise from priority blocks, where only a subset of channels is allowed, and from time-preference windows that introduce bonuses for specific genres.

The objective combines program scores with preference bonuses and subtracts penalties for truncation and channel switching.

---

## Algorithmic Structure

The implementation follows a structured pipeline:

1. **Segment generation**
   Each program is transformed into a set of feasible segments by clipping to the horizon, extracting minimum-duration slices, and aligning segments with preference windows and priority blocks.

2. **Segment scoring**
   Each segment is assigned a value combining base score, preference bonuses, and truncation penalties.

3. **Candidate reduction**
   Only the top-$K$ segments per program are retained. This step controls the size of the search space while preserving high-quality candidates.

4. **Dynamic programming optimization**
   The remaining segments are sorted in temporal order and processed using a dynamic programming recurrence that enforces temporal compatibility, genre continuity, and switching penalties.

5. **Deterministic repair**
   If multiple segments from the same program appear in the solution, weaker occurrences are removed and the optimization is repeated until uniqueness is achieved.

---

## Determinism and Termination

The deterministic baseline is fully deterministic. It does not rely on randomness, and all tie-breaking rules are resolved in a fixed and reproducible manner. For a fixed input instance and identical configuration, repeated executions produce identical schedules and scores.

Termination is guaranteed. The segment generation phase produces a finite set of candidates. The dynamic programming phase processes this set in a single forward sweep. The duplicate-elimination procedure is bounded by a fixed maximum number of iterations and removes at least one conflicting segment in each step, ensuring convergence in practice.

---

## Complexity Analysis

Let $N$ denote the number of programs, $K$ the maximum number of retained segments per program, and $R$ the maximum allowed genre streak.

After candidate reduction, the number of segments is bounded by $M = O(NK)$. The dynamic programming phase processes segments in temporal order and evaluates transitions using compact predecessor structures. Under this implementation, each state update requires constant or near-constant time per genre state, yielding an overall complexity of approximately $O(MR)$.

Substituting $M = O(NK)$, the optimization phase runs in approximately $O(NK \cdot R)$.

Segment generation and pruning introduce additional overhead but do not change the dominant complexity of the dynamic programming stage.

---

## Scope of Optimality

The dynamic programming procedure computes an optimal solution with respect to the retained segment set. The full method is therefore exact on this restricted search space.

The overall algorithm is not globally exact for the original problem, since candidate generation and top-$K$ pruning limit the set of feasible decisions considered during optimization.

---

## Limits of Guarantees

This implementation does not provide a formal approximation ratio or a theoretical optimality bound for the complete problem. Establishing such guarantees would require additional assumptions on the structure of the candidate set and the pruning strategy.

Reported comparisons against alternative methods, including ILP-based approaches, should be interpreted as empirical rather than theoretical.

---

## Practical Behavior

The method is particularly effective in instances where temporal flexibility plays a significant role, such as dense IPTV and streaming scenarios. In these settings, segment-level modeling enables the scheduler to exploit overlaps and alignments that are not accessible under strict program-level formulations.

The quality of the solution depends on the richness of the generated segments and the choice of the parameter $K$. Smaller values reduce computational cost but may limit the search space, while larger values improve coverage at the expense of runtime.
