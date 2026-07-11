# Methodology

This document summarizes the algorithmic method implemented in the repository. The code supports three related solvers: a deterministic baseline, a hybrid Genetic Algorithm, and a Genetic Algorithm followed by local search.

## Problem Model

Each input instance defines a fixed operating horizon, several TV channels, and a list of programs per channel. A program has a start time, end time, genre, and score. The solver selects non-overlapping program segments to form a schedule for one display.

Hard constraints include:

- selected segments must lie inside the operating horizon;
- selected segments must not overlap;
- selected segments must satisfy the minimum duration rule;
- priority blocks restrict which channels may be shown during specific intervals;
- the schedule must not exceed the maximum allowed streak of consecutive programs with the same genre.

The objective combines:

- program score;
- bonuses from genre-time preferences;
- channel-switch penalties;
- partial-broadcast termination penalties.

## Deterministic Baseline

The deterministic solver first generates feasible candidate segments by clipping programs to the operating horizon and to relevant boundary points from priority blocks and preference windows. It then keeps the best `top_k` candidate segments for each program.

The reduced candidate set is solved with a dynamic-programming recurrence over time-compatible segments. State information tracks genre continuity and channel switching. A bounded duplicate-removal loop repairs repeated uses of the same program.

This baseline is used both as an independent method and as the seed solution for the Genetic Algorithm.

## Genetic Algorithm

An individual is a candidate schedule represented as a list of selected segments. The initial population contains the deterministic seed and randomized variants of it.

The GA uses:

- tournament selection;
- elitism;
- time-cut crossover;
- block-mix crossover;
- segment replacement mutation;
- weak-segment deletion;
- gap insertion;
- boundary expansion;
- block rebuild mutation;
- repair after crossover and mutation.

The repair procedure removes infeasible segments, resolves overlaps, enforces priority-block restrictions, limits repeated programs, fixes excessive genre streaks, and attempts to fill useful gaps.

The GA runs for a time budget and records the best feasible schedule found.

## Local Search

The local-search variant starts from the best GA schedule and applies greedy neighborhood moves. Candidate moves include replacing a segment with a nearby alternative, inserting into free gaps, expanding partial broadcasts, removing weak segments, rebuilding small blocks, and choosing same-channel continuations to reduce switching penalties.

Each candidate is repaired and accepted only when it improves the objective score. This phase is intended as intensification around the best solution found by the GA.

## Reproducibility Notes

GA and local-search runs use explicit seeds. Batch scripts derive per-run seeds from a base seed and the execution index. Small differences in runtime can occur across machines because the primary stopping condition is time-based.

For exact artifact inspection, use the checked-in JSON and CSV outputs. For independent reruns, use the scripts documented in `docs/reproducibility.md`.
