# Modules Directory

## Purpose
Core tool implementations and business logic. Each tool is wrapped in a `run()` function for unified app integration while maintaining standalone capability.

## Architecture Pattern

Each module follows this structure:
```python
def run():
    """Main entry point when called from unified app"""
    # Tool logic here

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    run()
```

## Files

### `top_stacks.py`
**Purpose**: Game stack analysis and boom/bust player identification

**Key Features**:
- Game environment scoring with pace metrics (ITT, total points)
- PROE (Pass Rate Over Expected) integration for game script analysis
- **Game Script Projections**: Blowout probability and position-specific impacts
- QB + bring-back combinations (WR/TE/RB correlations)
- Boom/Bust probability calculations (ceiling vs projection)
- Leverage scoring (Boom% - Ownership%)
- Player filtering by position, salary, ownership, leverage, game script
- Sharp Football metrics integration (EPA, Explosive Play Rate, PPD)
- Correlation model using historical weekly performance

**Game Script Analysis**:
- **Blowout Probability**: Normal distribution (std dev ~13.5 points) calculates likelihood of 14+ point margin
- **Script Categories**:
  - 🔥 Blowout (Fav): Spread >7, run-heavy game script expected
  - ❄️ Blowout (Dog): Spread <-7, garbage time passing expected
  - ⚡ Shootout: Total ≥50, high-volume passing game
  - ⚖️ Competitive: Close game, balanced approach
  - 🛡️ Low-Scoring: Total <44, defensive battle
- **Position Impacts** (multipliers applied to ceiling):
  - RB: +20% as favorite (run clock), -15% as underdog
  - QB: +15% in shootouts, +10% as underdog (garbage time)
  - WR: +12% in shootouts, +8% as underdog
  - TE: +8% in shootouts, +5% competitive
  - DST: +25% as underdog (sacks/turnovers), +15% low-scoring
- **Implementation**: Uses existing Matchup.csv (Spread, Total, ITT) - no new data required

**Leverage Enhancements**:
- Leverage filter slider (min-max range)
- Sort by leverage checkbox
- Leverage categories: 🔥 High (≥10%), ⚡ Medium (5-10%), ✓ Low (0-5%), ⚠️ Negative (<0%)
- Color-coded categories and insights summary
- Multi-criteria filtering (Position + Salary + Ownership + Leverage + Game Script)

**Correlation Model**:
- Uses `weekly_stats.csv` to identify player roles (WR1, WR2, TE1, RB1)
- Calculates within-team correlations (QB-WR, WR-WR, QB-TE)
- Time-series correlation over rolling windows
- Informs stacking decisions in optimizer

**Technical Details**:
- Loads ROO projections as primary data source
- Maps columns: `hist_max_fpts` → `max_dk`, `hist_mean_fpts` → `avg_dk`
- Calculates `hits_4x` from historical games (4x salary value threshold)
- DST hits_4x uses `Weekly_DST_Stats.csv` (position-aware lookup)
- Merges matchup data, PROE, Sharp metrics
- Generates weighted opportunity and concentration scores
- scipy.stats for game script probability calculations

### `sims_tool.py`
**Purpose**: Full-slate lineup simulation against field competition

**Architecture**:
1. **Data Ingestion**:
   - `players.csv` - Projections + ownership
   - `Weekly_Stats.csv` - Historical per-game outcomes
   - `matchup.csv` - Game totals/spreads/efficiency
   - `lineups.csv` - User lineups to evaluate

2. **Precomputation**:
   - Player outcome distributions (from historical data)
   - Game environment models (team scoring multipliers)
   - Correlation lookups (QB-WR, RB-team total)

3. **Simulation Loop** (N=10,000+ iterations):
   - Simulate game environments (spread/total variance)
   - Sample player scores with lognormal distribution
   - Apply team adjustments (pace, pass rate, rush rate)
   - Apply correlations (QB-pass catcher boom/bust)
   - Generate field lineups (ownership-weighted)
   - Rank user lineups vs field
   - Map ranks to contest payouts

4. **Output**:
   - Mean score, mean profit, ROI
   - Cash probability, Top 10%, Top 1%, Top 0.1%
   - Distribution histograms

**Key Technical Implementations**:
- **Player History**: Lognormal distribution from `hist_mean_fpts`, `effective_std_fpts`
- **Game Environment**: `build_env_state()` - spread/total sim with variance
- **Correlations**: QB boom → WR boost (1.1-1.3x), QB bust → WR penalty (0.7-0.9x)
- **Field Generation**: Ownership-weighted sampling with salary constraints
- **Vectorization**: NumPy arrays for 10K+ sim performance

**Contest Types Supported**:
- NFL $25K Sunday Clutch (Top 4,416 pay)
- NFL $175K Fair Catch (Top 39,225 pay)
- NFL $3.5M Sunday Million (Top 236,842 pay)
- Custom payout structures

**DST Integration**:
- DST name standardization ("Cleveland Browns" → "Browns")
- Full season volatility from `Weekly_DST_Stats.csv`
- Spread correlation (favorites get boost)

### `pre_contest_sim.py`
**Purpose**: Pre-lineup-lock player pool optimization

**Features**:
- ROO projections with floor/ceiling
- Exposure optimization recommendations
- Volatility analysis per player
- Player pool selection guidance
- Risk/reward profiling

**Use Case**: Identify which players to include in optimizer before building lineups

### `ownership_adjuster.py`
**Purpose**: Normalize ownership projections to DraftKings roster rules

**Features**:
- Position-based normalization (1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX, 1 DST)
- Ensures ownership sums correctly across positions
- Roster construction compliance
- Bulk ownership adjustments
- CSV import/export

**Algorithm**:
1. Sum ownership by position
2. Calculate normalization factors
3. Scale individual player ownership
4. Validate totals match roster constraints

## Key Responsibilities
- Data processing and transformations
- Statistical calculations (correlations, projections, volatility)
- Monte Carlo simulation logic
- Player/team/game modeling
- Tool-specific business rules

## Data Flow
```
ROO Simulator (roo_simulator.py)
    ↓ (generates roo_projections.csv)
Modules (load data)
    ↓
Processing (calc correlations, build models)
    ↓
Pages (UI rendering)
```

## Usage
These modules are called by pages in the Streamlit app via their `run()` functions. They handle all computation and return data structures for UI rendering. Can also be run standalone for development/testing.
