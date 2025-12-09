# DFS Tools Suite - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- Multiple projection source support
- Lineup builder with in-app optimizer
- Bankroll management tools

---

## [2025-12-08]

### Added
- `claude.md` files in all subdirectories for AI context
- `plan.md` for tracking future enhancements
- `changelog.md` for version tracking

### Changed
- **ROO Simulator**: Now uses FULL SEASON data for all metrics (mean, std, min, max)
  - Previously used 8-week lookback for mean/std, causing inconsistency
  - `hist_max_fpts` (max_dk) now shows true season ceiling
  - `hist_mean_fpts` (avg_dk) now shows true season average
  - Coefficient of variation now mathematically consistent

### Removed
- Consolidated 12 extraneous docs from `/docs` into `claude.md` files:
  - MODULARIZATION_SUMMARY.md
  - UNIFIED_APP.md
  - DST_INTEGRATION.md
  - CORRELATION.md
  - top_stacks_stokastic.md
  - sims_tool_instructions.md
  - MODULAR_REORGANIZATION.md
  - MODULAR_STRUCTURE.md
  - modular_instructions.md
  - PIPELINE_SIMPLIFICATION.md
  - OPTIMIZATION_SUMMARY.md
  - NEW_DATA_STRUCTURE.md

---

## [2025-12-07]

### Added
- **Lineup Simulator**: DST name standardization for lineup parsing
  - Maps DraftKings full names ("Cleveland Browns") to abbreviated format ("Browns")
  - Fixes "player not found" errors when importing lineups with DST
  - Applied same 32-team mapping used in ROO simulator

- **Boom/Bust Tool**: Salary and ownership filter sliders
  - Salary range slider ($min-$max, $100 steps)
  - Ownership percentage slider (0%-max%, 0.5% steps)
  - 4-column filter layout for better UX
  - Multi-criteria filtering (position + salary + ownership)

### Fixed
- Top Stacks tool position filtering (variable shadowing bug)
- QB-RB correlation display logic
- None value formatting in correlation output

### Changed
- Stack generation optimization: Pre-load Weekly_Stats.csv once (80%+ faster)
- Eliminated 4,500+ redundant file reads in stack combinations

---

## [2025-11-30] - DST Integration

### Added
- **ROO Simulator**: Full DST (Defense/Special Teams) support
  - Loads `Weekly_DST_Stats.csv` separately from offensive players
  - Full season lookback (weeks 1-13) instead of 8-week window
  - DST name standardization mapping (32 teams)
  - Position-level fallbacks for low-sample DST units
  - Default projections for missing DST (9 pts, 2% ownership)

- **Lineup Simulator**: DST integration
  - DataManager integration for global data loading
  - ROO projection column mapping (`effective_std_fpts`, `OWS_Proj_Own`)
  - Player history from ROO data using lognormal distribution
  - Game environment state building (`build_env_state()`)
  - DraftKings lineup parsing with Entry ID filtering
  - NFL $175K Fair Catch contest structure

### Changed
- **ROO Simulator**: Changed merge strategy from `inner` to `left`
  - Keeps all players from salary file
  - Prevents DST from being dropped during merge
- **ROO Simulator**: Trim trailing spaces from DST names
- **ROO Simulator**: Lookback window expanded for DST volatility

### Fixed
- DST not appearing in ROO projections (multiple root causes)
- Missing player history functions in lineup simulator
- Type conversion errors (Series vs scalar)
- Array dimension issues with single lineup
- DraftKings lineup format parsing

---

## [2025-11-15] - Unified App Launch

### Added
- **Unified Application**: Single `app.py` with multi-page structure
  - Sidebar navigation between all tools
  - One-click launch via `launch_dfs_tools.bat`
  - Home page with tool descriptions and quick links

- **Modular Architecture**: All tools wrapped in `run()` functions
  - `modules/top_stacks.py`
  - `modules/sims_tool.py`
  - `modules/pre_contest_sim.py`
  - `modules/ownership_adjuster.py`

- **Streamlit Pages Structure**:
  - `pages/1_🏠_Home.py`
  - `pages/2_⭐_Top_Stacks.py`
  - `pages/3_📊_Lineup_Simulator.py`
  - `pages/4_🎲_Pre_Contest_Simulator.py`
  - `pages/5_🦃_Ownership_Adjuster.py`
  - `pages/6_🏆_Contest_Analyzer.py`

### Changed
- All tools now support both unified app and standalone execution
- Commented out `st.set_page_config()` in modules (handled by main app)

---

## [2025-10-01] - Correlation Model

### Added
- **Correlation Module**: Within-team player correlation calculator
  - Identifies player roles (QB1, WR1, WR2, TE1, RB1) by usage
  - Builds week-by-week DK_Points time series
  - Calculates Pearson correlation matrix
  - Extracts specific pairs (QB-WR1, QB-WR2, WR1-WR2, etc.)
  - Supports rolling window correlation (last 5 weeks)

- **Top Stacks Tool**: Correlation integration
  - Displays QB-RB correlation scores
  - Informs stacking recommendations
  - Highlights negative correlations (cannibalization)

---

## [2025-09-15] - ROO Simulator Initial Release

### Added
- **ROO (Range of Outcomes) Simulator**: Monte Carlo projection engine
  - Historical volatility calculation from `Weekly_Stats.csv`
  - Position-level fallbacks for low-sample players
  - Matchup adjustments via Sharp Football metrics
  - PROE (Pass Rate Over Expected) integration
  - Floor/Ceiling projections (15th/85th percentiles)
  - Full percentile distribution (P5, P10, P25, P50, P75, P90, P95)
  - Volatility Index calculation
  - Outputs `roo_projections.csv`

---

## [2025-08-01] - Initial Tools

### Added
- **Top Stacks Tool**: Game stack analysis
  - QB + bring-back combinations
  - Game environment scoring (ITT, total, pace)
  - Sharp metrics integration
  - Boom/Bust player identification

- **Lineup Simulator**: Full-slate simulation
  - Monte Carlo simulation (10,000+ iterations)
  - Game correlation modeling
  - Field lineup generation
  - Contest payout mapping
  - ROI and probability calculations

- **Pre-Contest Simulator**: Player pool optimization
  - Exposure recommendations
  - Volatility analysis
  - Risk/reward profiling

- **Ownership Adjuster**: Ownership normalization
  - Position-based constraints
  - Roster construction compliance

---

## Version Guidelines

**Major changes**: New tools, significant architecture changes
**Minor changes**: New features, data integrations
**Patches**: Bug fixes, performance improvements

**Categories**:
- `Added` - New features
- `Changed` - Changes to existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Vulnerability fixes
