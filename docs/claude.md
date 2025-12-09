# Documentation Directory

## Purpose
Project documentation, guides, and technical specifications. This directory contains comprehensive architecture docs, tool-specific guides, and implementation notes.

## Application Structure

### Unified App (`UNIFIED_APP.md`, `MODULARIZATION_SUMMARY.md`)

**Before Modularization**:
- 4 separate Streamlit apps requiring individual launches
- Each with `st.set_page_config()` causing import conflicts
- No unified navigation

**After Modularization**:
- Single `app.py` with sidebar navigation
- All tools in `modules/` wrapped in `run()` functions
- Backward compatible (standalone files still work)
- One-click launch via `launch_dfs_tools.bat`

**File Structure**:
```
dfsdude-tools/
├── app.py                    # Main unified launcher
├── modules/                  # Modularized tools with run()
├── pages/                    # Streamlit multi-page structure
├── components/               # Reusable UI elements
├── services/                 # Shared algorithms
├── utils/                    # Config and helpers
└── data/                     # Data loading
```

## Core Documentation

### `QUICK_START.md`
Quick reference for launching tools and basic workflow.

### `README.md`
Main project overview and setup instructions.

### `ROO_README.md`
**ROO (Range of Outcomes) Simulator Documentation**

Generates Monte Carlo-based projections with:
- Floor/Ceiling (15th/85th percentiles)
- Median projections
- Volatility Index
- Matchup adjustments (PROE integration)
- Historical volatility from full season data

**Key Changes** (from recent updates):
- Uses **FULL SEASON** data for all metrics (mean, std, min, max)
- DST name standardization ("Denver Broncos" → "Broncos")
- Left merge strategy (keeps all salary players)
- Default projections for missing DST (9 pts, 2% own)
- Coefficient of variation from consistent time windows

### `DST_INTEGRATION.md`
**Defense/Special Teams Implementation**

**Data Source**: `Weekly_DST_Stats.csv`
- Schema: Player, Team, Week, Opp, Fum, DST_TD, Int, SACK, Safety, Points_Against, DK_Points
- Full season lookback (weeks 1-current)

**Processing**:
1. Load `Weekly_DST_Stats.csv` separately from offensive players
2. Standardize names using mapping dict (32 teams)
3. Calculate volatility metrics (count, mean, std, min, max)
4. Assign Position = 'DST'
5. Concatenate with offensive players
6. Apply same effective_std logic with position fallbacks

**Benefits**:
- Complete slate coverage (all DK positions)
- DST boom/bust probabilities
- Matchup adjustments via opponent offensive metrics
- Correlation with spread (favorites get boost)

**Name Standardization** (applied in both `roo_simulator.py` and `sims_tool.py`):
```python
dst_name_to_short = {
    'Arizona Cardinals': 'Cardinals',
    'Cleveland Browns': 'Browns',
    'Minnesota Vikings': 'Vikings',
    # ... all 32 teams
}
```

### `CORRELATION.md`
**Within-Team Player Correlation Model**

**Purpose**: Compute QB-WR, WR-WR, QB-TE correlations using `weekly_stats.csv`

**Approach**:
1. **Identify Roles** (per team):
   - QB1: Max `Pass_Att`
   - WR1: Max `Targets`
   - WR2: 2nd highest `Targets`
   - TE1: Max `Targets` (TE only)
   - RB1: Max `Weighted_Opportunities`

2. **Build Time Series**:
   - Week-by-week `DK_Points` for each player
   - Pivot to wide matrix (weeks × players)

3. **Calculate Correlations**:
   - Pearson correlation across weeks
   - Rolling window options (e.g., last 5 weeks)
   - Full season correlation

4. **Extract Pairs**:
   - QB ↔ WR1, QB ↔ WR2, QB ↔ TE1
   - WR1 ↔ WR2 (check for cannibalization)
   - WR1 ↔ TE1

**Use Cases**:
- Inform stacking rules in optimizer
- Evaluate teammate performance coupling
- Identify negative correlations (target competition)

### `MODULARIZATION_SUMMARY.md`
Detailed technical implementation of the unified app pattern:
- Wrapping tools in `run()` functions
- Commenting out `st.set_page_config()` in modules
- Standalone execution blocks
- Benefits for users and development

## Tool-Specific Documentation

### `top_stacks_stokastic.md`
**Top Stacks Methodology** (Stokastic-inspired)

**Key Concepts**:
- **Top Stack Probability**: Chance that QB + 1-2 pass catchers will be highest-scoring combo
- **Value**: Top stack probability per $1K salary
- **Rush %**: Expected team rush rate (lower = more passing)
- **Rating**: 0-100 score combining probability, value, and ownership

**Philosophy**:
- Focus on passing only (QB+WR/TE/RB receiving)
- Exclude RB rushing to avoid false positives
- Compare stack potential to QB ownership
- Identify undervalued stacks (high probability, low ownership)

### `sims_tool_instructions.md`
**Lineup Simulator Architecture** (621 lines)

Comprehensive technical specification covering:
- Data ingestion schemas
- Player↔stats↔matchup mapping
- Outcome distribution building (lognormal)
- Game environment simulation
- Correlation modeling
- Field lineup generation
- Contest payout structures
- Vectorization for performance

**See modules/claude.md for detailed summary**

### `boom_bust_tool.md`
Boom/Bust probability calculation methodology.

### `review_sims_tool.md`
Post-contest analysis tool for reviewing actual results.

### `ownership_projections.md`
Ownership modeling and normalization techniques.

### `POST_CONTEST_SIMS.md`
Post-contest simulation and analysis workflows.

### `PIPELINE_SIMPLIFICATION.md`
Data pipeline optimization notes.

### `OPTIMIZATION_SUMMARY.md`
Performance optimization changes.

### `NEW_DATA_STRUCTURE.md`
Data schema and file format specifications.

## Recommended Workflow

1. **Generate ROO Projections**:
   ```bash
   python roo_simulator.py
   ```
   Creates `roo_projections.csv` with Monte Carlo projections.

2. **Launch Unified App**:
   ```bash
   streamlit run app.py
   ```

3. **Pre-Contest Research**:
   - Use Pre-Contest Simulator for player pool
   - Use Top Stacks Tool for game environments
   - Use Boom/Bust filtering for leverage plays

4. **Build Lineups** (external optimizer)

5. **Validate Lineups**:
   - Use Lineup Simulator for contest simulation
   - Check ROI, cash %, top-finish %

6. **Post-Contest**:
   - Use Contest Analyzer to review results

## Data Requirements

**Location**: `C:\Users\schne\Documents\DFS\2025\Dashboard\`

**Required Files**:
- `Salaries_2025.csv` - DK player salaries
- `Weekly_Stats.csv` - Historical player performance
- `Weekly_DST_Stats.csv` - Historical DST performance
- `Matchup.csv` - Vegas lines (ITT, Spread, Total)
- `sharp_offense.csv` - Team offensive metrics
- `sharp_defense.csv` - Team defensive metrics
- `weekly_proe_2025.csv` - Pass Rate Over Expected
- `roo_projections.csv` - Output from ROO simulator

**Optional**:
- `Player_Mapping.csv` - Name standardization (1869 mappings)
- `projections_2025.csv` - Third-party projections

## Usage
Reference these documents when:
- Working on specific features
- Understanding system architecture
- Debugging data pipeline issues
- Adding new tools or features
- Optimizing performance
