# Correlation Model (Using weekly_stats.csv)

## 1. Purpose

This document describes how to compute **within-team player correlations** using only the existing `weekly_stats.csv` file.

The goal is to produce **simple, DFS-usable correlation metrics** such as:

- QB ↔ WR1 correlation
- QB ↔ WR2 correlation
- QB ↔ TE1 correlation
- WR1 ↔ WR2 correlation
- WR1 ↔ TE1 correlation

These can be used to:
- Inform stacking rules in the optimizer
- Evaluate how closely teammate performances move together
- Identify cannibalizing situations (negative correlations)


---

## 2. Source Data: weekly_stats.csv

We assume the app has a weekly player-level stats file with at least the following columns:

- `Player`
- `Position`
- `Week`
- `Team`
- `Opp`
- `Targets`
- `Receptions`
- `Rec_TD`
- `Rec_Yds`
- `Rush_Att`
- `Rush_Yds`
- `Rush_TD`
- `Pass_Att`
- `Pass_Comp`
- `Pass_Yds`
- `Pass_TD`
- `Weighted_Opportunities`
- `Int`
- `Fumble_Lost`
- `DK_Points`

We will use `Team`, `Player`, `Position`, `Week`, and `DK_Points` for correlation, plus `Targets` and `Weighted_Opportunities` to identify WR1/WR2/TE1/RB1.


---

## 3. High-Level Approach

1. For each team and season (or dataset):
   - Identify key players: QB, WR1, WR2, TE1, RB1.
2. Build a **week-by-week DK_Points time series** for each player.
3. Pivot to a **wide matrix**: rows = weeks, columns = players, values = DK_Points.
4. Compute the **correlation matrix** across players.
5. Extract specific correlation pairs (QB ↔ WR1, WR1 ↔ WR2, etc.).
6. Optionally, compute these correlations:
   - For the full season up to that point.
   - Over a rolling lookback window (e.g. last 5 weeks).


---

## 4. Identifying Key Players (WR1, WR2, TE1, RB1)

For each (`Team`, `season`) or for the full dataset if season is not tracked:

1. Filter players by `Position`:
   - QBs: `Position == 'QB'`
   - WRs: `Position == 'WR'`
   - TEs: `Position == 'TE'`
   - RBs: `Position == 'RB'`

2. Define a ranking metric:
   - For WR/TE: total **Targets** across all weeks (or average Targets per week).
   - For RB: total **Weighted_Opportunities** or `Rush_Att + Targets` across all weeks.
   - QB is typically the only QB for that team; if multiple, choose the one with the most `Pass_Att`.

3. Select:
   - `QB1` = QB with max total `Pass_Att`.
   - `WR1` = WR with max total `Targets`.
   - `WR2` = WR with second-highest total `Targets`.
   - `TE1` = TE with max total `Targets`.
   - `RB1` = RB with max total `Weighted_Opportunities` (or `Rush_Att + Targets`).

Store a mapping table like:

| Team | QB1 | WR1 | WR2 | TE1 | RB1 |
|------|-----|-----|-----|-----|-----|


---

## 5. Building Weekly Time Series

For each team:

1. Filter `weekly_stats` to that team only.
2. For each of the key players (QB1, WR1, WR2, TE1, RB1), create a weekly series:

   - Index: `Week`
   - Value: `DK_Points`

3. Make sure that:
   - All relevant weeks appear in each series.
   - If a player did not play in a given week, set `DK_Points = 0` (to keep alignment).
   - Sort by `Week` ascending.

This can be accomplished via `pivot_table`:

```python
team_df = weekly_stats[weekly_stats["Team"] == team_name]

pivot_df = team_df.pivot_table(
    index="Week",
    columns="Player",
    values="DK_Points",
    aggfunc="sum"
).fillna(0)
```

This yields a matrix where:
- Rows = weeks
- Columns = all players on that team
- Values = DK_Points (missing values filled with 0)


---

## 6. Computing Correlations

For each team:

1. Compute the correlation matrix:

```python
corr = pivot_df.corr()
```

2. Extract correlation pairs using the key player names:

```python
corr_qb_wr1 = corr.loc[QB1, WR1]  # QB ↔ WR1
corr_qb_wr2 = corr.loc[QB1, WR2]  # QB ↔ WR2
corr_qb_te1 = corr.loc[QB1, TE1]  # QB ↔ TE1

corr_wr1_wr2 = corr.loc[WR1, WR2]  # WR1 ↔ WR2
corr_wr1_te1 = corr.loc[WR1, TE1]  # WR1 ↔ TE1
corr_rb1_wr1 = corr.loc[RB1, WR1]  # RB1 ↔ WR1 (optional)
```

3. Save these to a summary table per team:

| Team | corr_qb_wr1 | corr_qb_wr2 | corr_qb_te1 | corr_wr1_wr2 | corr_wr1_te1 | corr_rb1_wr1 |
|------|-------------|-------------|-------------|--------------|--------------|--------------|


---

## 7. Rolling (Windowed) Correlations (Optional)

Instead of one correlation value for the full dataset, we can calculate a **rolling correlation** up to each week.

For each team:

1. Sort `pivot_df` by `Week`.
2. Define a lookback window (e.g. `lookback = 5` weeks).
3. For each week `W` (starting when enough data exists, `W >= lookback`):
   - Subset `pivot_df_window = pivot_df.loc[W-lookback+1 : W]`
   - Compute `corr_window = pivot_df_window.corr()`
   - Extract the same pairs as above (QB ↔ WR1, etc.)
   - Store these with `Team` and `Week = W`.

This generates a `team_correlations_by_week` table:

| Team | Week | corr_qb_wr1 | corr_qb_wr2 | corr_qb_te1 | corr_wr1_wr2 | corr_wr1_te1 |
|------|------|-------------|-------------|-------------|--------------|--------------|


---

## 8. Integration with Existing App

Once correlation tables are computed, integrate as follows:

1. **Static season-level correlations**:
   - Join `team_correlations` on `Team` into:
     - Simulation inputs
     - Stack selection logic
   - Helps choose which teams are ideal for double stacks, RB+WR combos, etc.

2. **Weekly rolling correlations**:
   - Join `team_correlations_by_week` on (`Team`, `Week`) into the main weekly player data.
   - Use as features in:
     - Range-of-outcomes modeling
     - Game selection / stack rules
     - Slate-specific heuristics

3. Naming convention:
   - Use clear column names like:
     - `QB_WR1_corr_season`
     - `QB_WR1_corr_last5`
     - `WR1_WR2_corr_season`
     - etc.


---

## 9. Interpretation Guidelines

- **High positive correlation (0.5 to 0.9)**:
  - Players often spike together.
  - Good targets for stacking (QB+WR1, WR1+WR2, QB+WR1+TE1, etc.).

- **Near-zero correlation (-0.2 to 0.2)**:
  - Performances are largely independent.
  - Stacks still valid in the right game environment, but correlation doesn’t provide an extra edge.

- **Negative correlation (< -0.3)**:
  - One player often benefits at the expense of the other.
  - Be cautious about double-stacking these pairs (e.g., WR1 vs RB1 in some offenses).


---

## 10. Implementation Notes

- Use `pandas` for all operations.
- Ensure consistent `Team` and `Player` naming across weeks.
- Consider filtering out players who:
  - Have fewer than 3–4 weeks of data (to avoid noisy correlations).
  - Have extremely low average DK_Points (non-rotational backups).

- All correlation calculations should be done **within-team only**; do not cross teams.


---

## 11. Deliverables for Coding Agent

1. A Python module, e.g. `correlation_model.py`, that exposes:

   - `build_team_player_roles(weekly_stats) -> roles_df`
   - `compute_team_correlations(weekly_stats, roles_df) -> team_corr_df`
   - `compute_team_correlations_by_week(weekly_stats, roles_df, lookback=5) -> team_corr_by_week_df`

2. Functions should **not** modify inputs in place; always return new DataFrames.

3. No hardcoded file paths – accept DataFrames as input and return DataFrames for the rest of the app to handle persistence.
