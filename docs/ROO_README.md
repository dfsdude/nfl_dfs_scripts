# NFL DFS Range-of-Outcomes (ROO) Engine  
### Instructions for Coding Agent (Updated for Sharp Football Team Data)

This document describes how to build a **simulation-based range-of-outcomes tool** that produces **floor, median, and ceiling fantasy point projections** for NFL players for a given main slate.

The user already has:

- **Weekly player-level stats** (historical)
- **Team-level metrics from Sharp Football Analysis**, for both **offense** and **defense**
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
   - Historical volatility
   - Current role & OWS median projection
   - Matchup & team-level context (via Sharp Football offense/defense metrics)

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
- Optional: snap %, routes, etc., if available.

We will use this for **volatility estimation** and **role characterization**.

---

### 2.2. Team-Level Metrics (Sharp Football: Year-to-Date)

The user has **two** separate CSVs from Sharp Football:

#### 2.2.1. Offensive Team Metrics (`sharp_offense.csv`)

Columns:

- `Team`
- `EPA_Play`
- `Yards Per Play`
- `Points Per Drive`
- `Explosive Play Rate`
- `Down Conversion Rate`

These are **offensive, year-to-date** (YTD) metrics.

#### 2.2.2. Defensive Team Metrics (`sharp_defense.csv`)

Columns:

- `Team`
- `EPA_Play_Allowed`
- `Yards Per Play Allowed`
- `Points Per Drive Allowed`
- `Explosive Play Rate Allowed`
- `Down Conversion Rate Allowed`

These are **defensive, year-to-date** (YTD) metrics.

#### 2.2.3. Combined Team Metrics Table

Create a combined table `team_metrics` by merging offense and defense on `Team`:

- `Team`
- Offense:
  - `EPA_Play`
  - `Yards Per Play`
  - `Points Per Drive`
  - `Explosive Play Rate`
  - `Down Conversion Rate`
- Defense:
  - `EPA_Play_Allowed`
  - `Yards Per Play Allowed`
  - `Points Per Drive Allowed`
  - `Explosive Play Rate Allowed`
  - `Down Conversion Rate Allowed`

We will use:

- Offensive metrics for the **player’s team** to reflect general offensive quality.
- Defensive metrics for the **opponent** to reflect matchup difficulty.

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
- `Spread` (team line, from perspective of `Team`)
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
2. `ows_projections` (on `Week` + `Player` + `Team`)
3. `team_metrics` (join on `Team` and also on `Opp`).

For clarity in the merged table, you can prefix defensive columns related to the opponent, for example:

- For the player’s team (offense):  
  - `Team_EPA_Play`, `Team_Explosive_Play_Rate`, etc.
- For the opponent’s defense:
  - `Opp_EPA_Play_Allowed`, `Opp_Explosive_Play_Rate_Allowed`, etc.

This merged table is the **input universe** for the simulation.

---

## 3. Core Modeling Strategy

We will:

1. **Estimate historical volatility** of fantasy points for each player.
2. Use OWS median projection as the **center** of the distribution.
3. Use historical volatility, adjusted by the **Sharp team matchup context**, to set the **spread** of the distribution.
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
   - Last **1–2 seasons**, or
   - Last **X games** before the current week.
   - Exclude current week itself.

2. **Aggregates per player**:  
   For each (`Player`, `Team`, `Position`):

   - `hist_games` = number of games
   - `hist_mean_fpts` = `FantasyPoints`.mean()
   - `hist_std_fpts`  = `FantasyPoints`.std()
   - Optional:
     - `hist_max_fpts`
     - `hist_min_fpts`
     - `hist_cv` = std / mean

3. Apply **minimum games logic**:
   - If `hist_games < MIN_GAMES` (e.g., 4):
     - Fall back to **position-level volatility**:
       - Compute `position_mean_fpts`, `position_std_fpts` from all historical data for that position.
       - Or blend player data + position average.

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

### 4.3. Matchup Adjustment Factor Using Sharp Football Metrics

Create a function `get_matchup_multiplier(player_row)` that returns a scalar multiplier ≥ 0 to scale **volatility** (standard deviation) based on matchup.

Inputs (from `current_week_with_ows`):

For the player’s **team offense** (YTD):

- `Team_EPA_Play` (from `EPA_Play`)
- `Team_Explosive_Play_Rate` (from `Explosive Play Rate`)
- `Team_Points_Per_Drive` (from `Points Per Drive`)

For the **opponent defense** (YTD):

- `Opp_EPA_Play_Allowed`
- `Opp_Explosive_Play_Rate_Allowed`
- `Opp_Points_Per_Drive_Allowed`

Plus game context:

- `Implied_Team_Total`
- `Spread`

#### 4.3.1. League Averages

Precompute league averages across all teams:

- `league_avg_EPA_Play`
- `league_avg_Explosive_Play_Rate`
- `league_avg_Points_Per_Drive`
- `league_avg_EPA_Play_Allowed`
- `league_avg_Explosive_Play_Rate_Allowed`
- `league_avg_Points_Per_Drive_Allowed`
- `league_avg_implied_total` (from Vegas data across all teams that week)

#### 4.3.2. Compute Offensive & Defensive Scores

For the player’s team:

```text
off_epa_factor        = Team_EPA_Play / league_avg_EPA_Play
off_explosive_factor  = Team_Explosive_Play_Rate / league_avg_Explosive_Play_Rate
off_ppd_factor        = Team_Points_Per_Drive / league_avg_Points_Per_Drive

For the opponent defense:

def_epa_factor        = Opp_EPA_Play_Allowed / league_avg_EPA_Play_Allowed
def_explosive_factor  = Opp_Explosive_Play_Rate_Allowed / league_avg_Explosive_Play_Rate_Allowed
def_ppd_factor        = Opp_Points_Per_Drive_Allowed / league_avg_Points_Per_Drive_Allowed

Convert to one offensive “support” factor and one defensive “softness” factor, e.g.:

off_factor_raw = average(off_epa_factor, off_explosive_factor, off_ppd_factor)
def_factor_raw = average(def_epa_factor, def_explosive_factor, def_ppd_factor)


Use simple arithmetic mean.

#### 4.3.3. Incorporate Implied Total
it_factor_raw = Implied_Team_Total / league_avg_implied_total

#### 4.3.4. Combine and Clamp

Combine into a single factor that will scale volatility:

raw_matchup_score = off_factor_raw * def_factor_raw * it_factor_raw


Clamp to a reasonable window, e.g.:

matchup_vol_multiplier = clamp(raw_matchup_score, 0.8, 1.3)


So:

Tough matchup / low implied total → closer to 0.8 (less volatility, more “grindy”).

Soft matchup / high implied total → closer to 1.3 (more volatility and upside).

Return matchup_vol_multiplier.

Note: this multiplier will be applied to the standard deviation, not the median.

#### 4.4. Building the Distribution per Player

For each player in current_week_with_ows:

Get:

median_proj = OWS_Median_Proj

If NaN or 0, treat carefully or skip (see edge cases).

Lookup effective_std_fpts from player_volatility.

Apply matchup adjustment using Sharp metrics:

matchup_vol_multiplier = get_matchup_multiplier(player_row)
adj_std = effective_std_fpts * matchup_vol_multiplier


To avoid extreme values:

adj_std = max(adj_std, MIN_STD) where MIN_STD might be 3.0.

Optionally cap (adj_std <= MAX_STD).

4.4.1. Convert to Lognormal Params

We want a lognormal distribution with:

Median ≈ median_proj

Volatility scaled by adj_std.

Procedure:

Let m = max(median_proj, EPS) with, e.g., EPS = 0.1.

Let rel_std = adj_std / (m + 1e-6).

Define:

sigma_log = ln(1 + rel_std)
sigma_log = clamp(sigma_log, 0.2, 1.5)
mu_log    = ln(m)


This is a heuristic mapping: higher historical volatility (adjusted by matchup) → higher sigma_log.

Store for each player:

mu_log

sigma_log

If median_proj is extremely small, see edge cases below.

5. Simulation Engine
5.1. Configuration

Create a config object (or hardcode initially):

N_SIMULATIONS = 5000 (or 10,000+ if performance allows)

Percentiles to compute:

FLOOR_PERCENTILE = 0.15

CEILING_PERCENTILE = 0.85

Optionally: [0.1, 0.25, 0.5, 0.75, 0.9, 0.95].

Random seed for reproducibility:

e.g. np.random.seed(42)

5.2. Simulation Flow

We simulate final fantasy points per player using their lognormal distribution (no play-by-play).

Algorithm:

Construct players_df for the current week with:

Player

Team

Position

Salary

Opp

OWS_Median_Proj

mu_log

sigma_log

(Any Sharp-based matchup columns you want to keep for reference.)

Extract arrays:

mu_arr (shape: [num_players])

sigma_arr (shape: [num_players])

For each simulation s in 0..N_SIMULATIONS-1:

Draw a vector of scores:

sim_scores = np.random.lognormal(mean=mu_arr, sigma=sigma_arr)


Store in a 2D array scores_matrix of shape [N_SIMULATIONS, num_players]

For memory reasons, you can:

Accumulate summary stats online, or

Simulate in chunks.

6. Post-Processing & Summary Stats

After simulations:

Let scores_matrix be [N_SIMULATIONS, num_players].

Compute, for each player (axis=0):

percentiles = np.percentile(
    scores_matrix,
    [10, 15, 25, 50, 75, 85, 90, 95],
    axis=0
)


Map them into DataFrame columns:

Sim_P10

Sim_P15

Sim_P25

Sim_P50 (median)

Sim_P75

Sim_P85

Sim_P90

Sim_P95

Define key outputs:

Floor_Proj = Sim_P15 (or Sim_P10, configurable)

Median_Proj = OWS_Median_Proj (keep OWS as median anchor)

Ceiling_Proj = Sim_P85 or Sim_P90 (configurable)

Combine into an output DataFrame:

Week

Player

Team

Position

Salary

Opp

OWS_Median_Proj

OWS_Proj_Own

Floor_Proj

Ceiling_Proj

Sim_P10, Sim_P15, Sim_P25, Sim_P50, Sim_P75, Sim_P85, Sim_P90, Sim_P95

hist_std_fpts, volatility_index

(Optional) matchup_vol_multiplier, Team_EPA_Play, Opp_EPA_Play_Allowed, etc. for debugging/analysis.

7. Handling Edge Cases
7.1. Players with Little or No History

If hist_games is very low (e.g., < 2):

Use position-level averages + a slightly higher σ to reflect uncertainty.

Optionally weight by team offensive quality (e.g., higher volatility on explosive offenses).

7.2. Players with Zero or Tiny Median Projection

If OWS_Median_Proj is <= 0:

Either:

Exclude from simulation, or

Set median_proj = small_value (e.g., 0.5) and a moderate sigma_log, so most outcomes hover near 0 with occasional spikes.

7.3. Correlation Between Players (Future Enhancement)

This initial version treats players as independent. Future improvements could introduce:

Game-level random multipliers (pace/total), applied to all players in that game.

Explicit correlation structures (e.g., QB ↔ WR/TE, RB ↔ DST).

For now: independent lognormal draws per player.

8. Outputs & File Integration
8.1. Output Format

Write results to:

CSV file, e.g. WeekXX_SimProjections.csv, or

New sheet in an existing Excel workbook, e.g. "SimulatedROO".

Each row = one player on the slate.

Key fields for downstream DFS workflows:

Player

Team

Position

Salary

Opp

OWS_Median_Proj

Floor_Proj

Ceiling_Proj

OWS_Proj_Own

Plus optional percentiles and volatility/matchup diagnostics.

9. Validation & Sanity Checks

Add a basic validation script:

Visual checks:

Print top 10 ceilings for QB, RB, WR, TE.

Ensure ceilings are in reasonable ranges (e.g., QB ~35–45, WR ~30–40, etc.).

Ensure floors are non-negative and generally below medians.

Distribution checks:

For a few archetype players (stud WR, volatile deep threat, bell-cow RB), plot histograms of simulated scores to verify shape and spread look reasonable.

Historical consistency:

Compare simulated “4x salary hit rate” with historical 4x hit rates for players with stable roles. They should be roughly in the same ballpark.

10. Implementation Notes

Write code in modular fashion:

load_data()

build_player_volatility()

build_team_metrics() (merge Sharp offense/defense)

compute_matchup_multiplier()

build_distributions()

run_simulations()

summarize_results()

export_results()

Use configuration constants at top or in a separate config file:

N_SIMULATIONS

MIN_GAMES_FOR_PLAYER_VOL

MIN_STD, MAX_STD

FLOOR_PERCENTILE, CEILING_PERCENTILE

Ensure reproducibility:

Set random seed once at the start of the simulation.

11. Deliverables

The coding agent should deliver:

Python script or module, e.g. roo_simulator.py, that:

Reads input tables (paths can be parameterized),

Produces an output CSV / Excel sheet for a specified week.

Config file (optional), e.g. config_roo.json, for:

File paths

Number of simulations

Percentile choices

README-style usage instructions:

How to run the script from the command line,

Required input files and columns (including Sharp offense/defense),

Output descriptions.

The user will handle file path wiring, integration with their existing DFS pipeline, and future enhancements. The coding agent should focus on building a clean, testable, modular ROO engine according to the above specs, using the Sharp Football team-level inputs as the core matchup adjustment signal.