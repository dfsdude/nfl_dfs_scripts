# NFL DFS Range-of-Outcomes (ROO) Engine  
### Instructions for Coding Agent

This document describes how to build a **simulation-based range-of-outcomes tool** that produces **floor, median, and ceiling fantasy point projections** for NFL players for a given main slate.

The user already has:

- **Weekly player-level stats** (historical)
- **Team-level metrics** (EPA, explosive play rate, etc.)
- **Current week’s slate & matchups** with **implied team totals & spreads**
- **OneWeekSeason (OWS)**:
  - Median projection (per player)
  - Projected ownership (per player)

The goal is **NOT** to model ownership.  
The goal is to produce **floor / ceiling projections via simulations** and write them back to a slate-level table.

---

## 1. High-Level Overview

We want to:

1. **Build a distribution of fantasy points** for each player based on:
   - Their historical volatility
   - Their current role & OWS median projection
   - Matchup & team-level context

2. **Run Monte Carlo simulations** (e.g., 5,000+ iterations) for the current week:
   - In each sim, generate a fantasy score for every player.
   - Collect all simulated scores per player.

3. **Extract percentiles** from the simulated distribution:
   - Floor projection = e.g. 15th percentile.
   - Median projection = 50th percentile (can use OWS median or simulated).
   - Ceiling projection = e.g. 85th or 90th percentile.

4. **Output a table** keyed by player with:
   - Median, Floor, Ceiling projections
   - Optional additional percentiles and metadata.

---

## 2. Input Data & Schemas

### 2.1. Historical Player-Level Stats

Assume a CSV or table, e.g. `weekly_stats`:

- `Season`
- `Week`
- `Player`
- `Position`
- `Team`
- `Opp`
- `FantasyPoints` (site-specific, e.g., DraftKings)
- Usage & efficiency fields (examples):
  - `Pass_Att`, `Pass_Comp`, `Pass_Yds`, `Pass_TD`, `Int`
  - `Rush_Att`, `Rush_Yds`, `Rush_TD`
  - `Targets`, `Receptions`, `Rec_Yds`, `Rec_TD`
- Optional: snap % or routes, etc., if available.

We will use this for **volatility estimation** and **role characterization**.

---

### 2.2. Team-Level Metrics

Assume a table, e.g. `team_metrics`:

- `Season`
- `Week`
- `Team`
- `Offensive_EPA_per_play`
- `Defensive_EPA_per_play`
- `Explosive_Play_Rate_Off`
- `Explosive_Play_Rate_Def`
- Optional: `Pace`, `PROE`, `Run_Rate`, etc.

We’ll use these for **matchup/context adjustments** (e.g., easier/harder games).

---

### 2.3. Current Week Slate & Vegas Info

Assume a table, e.g. `current_slate`:

- `Week`
- `Player`
- `Position`
- `Team`
- `Opp`
- `Salary`
- `Game_ID` or (`Team`, `Opp`, `Home/Away`)
- `Implied_Team_Total`
- `Spread` (team line, from perspective of Team)
- Optional:
  - `Game_Total`
  - `Home_Away` flag

This is the **core player list** we’re computing projections for.

---

### 2.4. OWS Projections & Ownership

Assume a table, e.g. `ows_projections`:

- `Week`
- `Player`
- `Team`
- `Position`
- `OWS_Median_Proj`  (fantasy points)
- `OWS_Proj_Own`     (ownership %)

For this tool:

- Use **`OWS_Median_Proj` as the central (median) projection** for each player.
- Keep `OWS_Proj_Own` as a pass-through column; do **not** model ownership here.

---

### 2.5. Integration

Create a **merged current-week table**, e.g. `current_week_with_ows`, by joining:

1. `current_slate`
2. `ows_projections` (on Week + Player + Team)
3. Optionally, team-level metrics for `Team` and `Opp` for the current week.

This merged table is the **input universe** for the simulation.

---

## 3. Core Modeling Strategy

We will:

1. **Estimate historical volatility** of fantasy points for each player.
2. Use OWS median projection as the **center** of the distribution.
3. Use historical volatility (and small matchup adjustments) to set the **spread** of the distribution.
4. Represent each player’s fantasy outcomes as a **lognormal distribution** (to avoid negative scores).
5. **Sample from that distribution** in a simulation loop.

---

## 4. Step-by-Step Implementation

### 4.1. Libraries & Setup

Use Python:

- `pandas`
- `numpy`
- `scipy.stats` (optional; useful for lognormal handling)
- Any configuration via a simple `.yaml` or `.json` file if desired.

---

### 4.2. Build Historical Volatility Table

Create a function that:

1. **Filters historical stats** to a reasonable window, e.g.:
   - Last **1–2 seasons**
   - Or last **X games** before the current week
   - Exclude current week itself.

2. **Aggregates per player**:
   For each (`Player`, `Team`, `Position`):

   - `hist_games` = number of games
   - `hist_mean_fpts` = `FantasyPoints`.mean()
   - `hist_std_fpts`  = `FantasyPoints`.std()  
   - Optional volatility metrics:
     - `hist_max_fpts`
     - `hist_min_fpts`
     - `hist_cv` = std / mean

3. Apply **minimum games logic**:
   - If `hist_games < MIN_GAMES` (e.g., 4):
     - Fall back to **position-level volatility**:
       - Compute `position_mean_fpts`, `position_std_fpts` from all historical data for that position.
       - Or weight player data + position average.

4. Save results as `player_volatility`:

Columns:

- `Player`
- `Team`
- `Position`
- `hist_games`
- `hist_mean_fpts`
- `hist_std_fpts`
- `effective_std_fpts` (after fallback/weighting)
- Optional: `volatility_index` (e.g., normalized std vs position).

---

### 4.3. Matchup Adjustment Factor (Simple Version)

Create a function `get_matchup_multiplier(player_row)` that returns a scalar multiplier ≥ 0.

Inputs (from merged `current_week_with_ows` + `team_metrics`):

- Offensive metrics for `Team`
- Defensive metrics for `Opp`
- `Implied_Team_Total`
- `Spread`

Example simple idea:

- Compute a baseline from implied total:
  - `IT_total = player_row['Implied_Team_Total']`
  - `baseline_IT = league_avg_implied_total` (pre-computed from historical league data)
  - `it_factor = IT_total / baseline_IT`

- Defensive EPA adjustment (relative to league avg):
  - If opponent defense is soft → small boost to volatility and/or mean
  - For simplicity: use the factor on std, not mean.

- Final `matchup_vol_multiplier`:
  - e.g. clamp `it_factor` to `[0.8, 1.2]`.

Return:
- `matchup_vol_multiplier` = e.g. between 0.8 and 1.2.

This will **scale the standard deviation**, not the OWS median.

---

### 4.4. Building the Distribution per Player

For each player in `current_week_with_ows`:

1. Get:
   - `median_proj = OWS_Median_Proj`
   - If NaN or 0, skip player or handle separately.
2. Lookup `effective_std_fpts` from `player_volatility`.
3. Apply matchup adjustment:
   - `adj_std = effective_std_fpts * matchup_vol_multiplier`.

To avoid extreme values:

- `adj_std = max(adj_std, MIN_STD)` where `MIN_STD` might be 3.0
- Optionally cap with `MAX_STD`.

#### 4.4.1. Convert to Lognormal Params

We want a **lognormal distribution** with:

- **Median ≈ `median_proj`**
- **Standard deviation roughly ≈ `adj_std`**

We can approximate as follows:

1. Let `m = max(median_proj, EPS)` (EPS small positive like 0.1).
2. Let `v = adj_std^2` (variance).

Using standard lognormal relationships:

- If `X ~ LogNormal(μ, σ²)` then:
  - median(X) = exp(μ)
  - mean(X)   = exp(μ + σ² / 2)
  - var(X)    = (exp(σ²) - 1) * exp(2μ + σ²)

We want **median = m**, and a reasonable variance:

- Set `μ = ln(m)`.
- Solve for `σ` using a heuristic instead of exact variance fit (to keep it simple and stable):

Example heuristic:

- Define a **relative variance factor**:
  - `rel_std = adj_std / (m + 1e-6)`
  - Set `σ = ln(1 + rel_std)`  (clamped between [0.2, 1.5])

This doesn’t perfectly match the variance, but it captures higher volatility when historical std is large relative to median.

Store for each player:

- `mu_log = ln(median_proj_clamped)`
- `sigma_log = resulting sigma`

If `median_proj` is extremely small (e.g. fringe player):

- You can reduce σ or skip lognormal convert and use a small normal bounded at 0.

---

## 5. Simulation Engine

### 5.1. Configuration

Create a config object (or hardcode initially):

- `N_SIMULATIONS = 5000` (or 10,000+ if performance allows)
- Percentiles to compute:
  - `floor_pct = 0.15`
  - `ceiling_pct = 0.85`
  - plus optional `[0.1, 0.25, 0.5, 0.75, 0.9, 0.95]`.

- Random seed for reproducibility:
  - e.g. `np.random.seed(42)`

---

### 5.2. Simulation Flow

We **do not need to simulate play-by-play**. We simulate **final fantasy points per player** using their lognormal distribution.

Algorithm:

1. Construct a `players_df` for the current week with:
   - `Player`
   - `Team`
   - `Position`
   - `Salary`
   - `Opp`
   - `OWS_Median_Proj`
   - `mu_log`
   - `sigma_log`

2. For performance:
   - Extract arrays:
     - `mu_arr` (shape: [num_players])
     - `sigma_arr` (shape: [num_players])

3. For each simulation `s` in `0..N_SIMULATIONS-1`:

   - Generate a vector of fantasy scores:

     ```python
     sim_scores = np.random.lognormal(mean=mu_arr, sigma=sigma_arr)
     ```

   - Optionally, add a very small chance of “0” games (injury / benched) via Bernoulli with small p, but only if we want.

   - Store sim_scores in a 2D array:
     - Shape: [N_SIMULATIONS, num_players]

   Memory options:
   - For large slates, you may:
     - Accumulate stats incrementally (online calculation),
     - Or split the simulations into chunks.

---

## 6. Post-Processing & Summary Stats

After simulations:

1. Let `scores_matrix` be [N_SIMULATIONS, num_players].

2. Compute, **for each player (axis=0)**:

   - `p10`, `p15`, `p25`, `p50`, `p75`, `p85`, `p90`, `p95`:
     ```python
     percentiles = np.percentile(scores_matrix, [10, 15, 25, 50, 75, 85, 90, 95], axis=0)
     ```

   Map them back into a DataFrame:

   - `Sim_P10`
   - `Sim_P15`
   - `Sim_P25`
   - `Sim_P50` (median)
   - `Sim_P75`
   - `Sim_P85`
   - `Sim_P90`
   - `Sim_P95`

3. Define **final floor/ceiling**:

   - `Floor_Proj`   = `Sim_P15` (or `Sim_P10`, per user preference)
   - `Median_Proj`  = `OWS_Median_Proj` (keep external median as the anchor)
   - `Ceiling_Proj` = `Sim_P85` or `Sim_P90`

4. Combine into an output DataFrame:

   Columns:

   - `Week`
   - `Player`
   - `Team`
   - `Position`
   - `Salary`
   - `Opp`
   - `OWS_Median_Proj`
   - `OWS_Proj_Own`
   - `Floor_Proj`
   - `Ceiling_Proj`
   - `Sim_P10`, `Sim_P15`, `Sim_P25`, `Sim_P50`, `Sim_P75`, `Sim_P85`, `Sim_P90`, `Sim_P95`
   - Any volatility indices (e.g., `hist_std_fpts`, `volatility_index`)

---

## 7. Handling Edge Cases

### 7.1. Players with Little or No History

If `hist_games` is very low (e.g., < 2):

- Use position-level averages + a **slightly higher σ** (they are uncertain).
- Optionally:
  - Combine team role data (depth chart) if available.
- If no data at all:
  - Set a very low median projection and a moderate σ.
  - Outcomes should cluster near zero.

### 7.2. Players with Zero or Tiny Median Projection

If `OWS_Median_Proj` is <= 0:

- Either exclude them from the sim,
- Or set `median_proj = small_value` (e.g., 0.5) and high σ so that most outcomes are ~0, with rare spikes.

### 7.3. Correlation Between Players (Future Enhancement)

This first version **does not model correlations between players** directly (each player is independent).

Future version could:

- Add game-level random factors (e.g., game pace or scoring multiplier),
- Apply correlation structures between QB and pass catchers, etc.

For now: **independent lognormal draws per player**.

---

## 8. Outputs & File Integration

### 8.1. Output Format

Write results to:

- CSV file (e.g., `WeekXX_SimProjections.csv`), or
- New sheet in existing Excel workbook, e.g. `"SimulatedROO"`.

Each row = player on the slate.

Key fields for downstream DFS workflows:

- `Player`
- `Team`
- `Position`
- `Salary`
- `Opp`
- `OWS_Median_Proj`
- `Floor_Proj`
- `Ceiling_Proj`
- `OWS_Proj_Own` (unchanged)
- Extra percentiles and volatility metrics as desired.

---

## 9. Validation & Sanity Checks

Add a basic validation script:

1. **Visual checks**:
   - Print top 10 ceilings for QBs, RBs, WRs, TEs.
   - Ensure ceilings look reasonable (e.g., QBs ~35–45, WRs ~30–40, etc.).
   - Ensure floors are not negative and mostly below medians.

2. **Distribution checks**:
   - For a few players (e.g., high-usage studs vs volatile deep threats), plot histograms of simulated scores and visually verify shapes.

3. **Consistency with historical data**:
   - Compare:
     - Historical % of games above 4x salary vs
     - Simulated % of games above 4x salary.
   - They should be in the same ballpark for players with stable roles.

---

## 10. Implementation Notes

- Write code in modular fashion:
  - `load_data()`
  - `build_player_volatility()`
  - `compute_matchup_multiplier()`
  - `build_distributions()`
  - `run_simulations()`
  - `summarize_results()`
  - `export_results()`

- Use configuration constants at top or in a separate config file:
  - `N_SIMULATIONS`
  - `MIN_GAMES_FOR_PLAYER_VOL`
  - `MIN_STD`, `MAX_STD`
  - `FLOOR_PERCENTILE`, `CEILING_PERCENTILE`

- Ensure **reproducibility**:
  - Set random seed once at the start of the simulation.

---

## 11. Deliverables

The coding agent should deliver:

1. **Python script or module**, e.g. `roo_simulator.py`, that:
   - Reads input tables (paths can be provided by the user later),
   - Produces an output CSV / Excel sheet for a specified week.

2. **Config file (optional)**, e.g. `config_roo.json`, for:
   - Paths
   - Number of simulations
   - Percentiles

3. **README-style usage instructions**:
   - How to run the script from the command line,
   - Required input files and columns,
   - Output descriptions.

The user will handle **file path wiring**, integration with their existing DFS pipeline, and optimizations later. The coding agent should focus on building a **clean, testable, modular ROO engine** according to the above specs.
