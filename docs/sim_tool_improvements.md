Key runtime bottlenecks (where they occur)
High defaults: 5,000 simulations and a 11,890-entry field sampled to ~1,189 lineups drive volume before any optimization. Lowering these defaults or adding “fast mode” presets would cut work immediately.

Correlation path copies the sim_scores dict for every lineup and then iterates to adjust, doubling work when correlations are enabled. That copy-per-lineup pattern is expensive across thousands of field lineups per sim.

Lineup scoring is fully Python-looped for both field and user lineups every simulation, followed by a pandas rank call over a Python list. The nested Python loops and repeated list allocations add up at n_sims × (field_lineups + user_lineups).

Field lineup generation retries up to 5× the target count and recomputes salaries via a dict lookup per build; with ~1,189 requested lineups that can churn heavily before simulation even starts.

Targeted optimizations
Volume controls

Ship a “quick test” preset (e.g., 200 sims, field sample 200) and a warning when n_sims × field_size_sim exceeds a threshold; this trims work up front and nudges users toward faster iterations.

Correlation path

Avoid sim_scores.copy() per lineup; keep a NumPy array of player scores indexed by integer IDs and pass views to correlation functions. If correlations must mutate, reuse a preallocated array and write in place, cutting thousands of dict copies per sim.

Cache correlation lookups (e.g., QB→receivers list, team/opponent mappings) once before the sim loop to reduce per-lineup pandas access inside apply_correlations.

Lineup scoring

Convert field and user lineups to integer index arrays once, then compute lineup scores with vectorized scores[lineup_idxs].sum(axis=1); rank with np.argsort/np.searchsorted instead of pandas rank. This removes Python loops over every lineup each simulation.

Preallocate all_scores arrays to avoid per-sim list growth, and reuse them to limit allocations.

Field lineup generation

Generate lineups with vectorized sampling (e.g., pre-sample positions as arrays) and stop retries once a target acceptance rate drops below a cutoff; log acceptance to help tune probabilities. This reduces long retry tails when salary-legal lineups are scarce.

Cache salaries as a NumPy array aligned to player IDs so validation is a fast array sum rather than repeated dict lookups.

General sim-loop hygiene

Move team_to_games and any other static mappings outside the button handler or compute them once before the sim loop to avoid repeated rebuilds.

If multiple user lineups are provided, compute shared per-sim structures (e.g., sim_scores array, correlation adjustments per team/game) once and broadcast instead of re-walking the same data for each lineup.

Implementing these changes will shrink per-simulation work, reduce allocations, and give users faster turnaround for exploratory runs.