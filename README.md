# 🏈 DFS Dude Tools

A complete suite of DFS (Daily Fantasy Sports) optimization and analysis tools for NFL contests.

## 🚀 Quick Start

### Launch the Unified Application

```bash
streamlit run app.py
```

Or double-click: `launch_dfs_tools.bat`

**All tools are accessed through the unified app:**
- ⭐ Top Stacks & Boom/Bust Tool
- 📊 DFS Lineup Simulator  
- 🎲 Pre-Contest Simulator
- 🦃 Ownership Adjuster
- 🏆 Contest Analyzer (Post-Contest)

**Features:**
- Single launch point for all tools
- Sidebar navigation between tools
- Consistent data pipeline
- Modular architecture with reusable components

See [UNIFIED_APP.md](docs/UNIFIED_APP.md) for complete documentation.

---

## 📚 Documentation

All detailed documentation is organized in the [`docs/`](docs/) folder:

### Architecture & Setup
- [MODULAR_STRUCTURE.md](docs/MODULAR_STRUCTURE.md) - Complete modular architecture guide
- [MODULAR_REORGANIZATION.md](docs/MODULAR_REORGANIZATION.md) - Refactoring summary
- [QUICK_START.md](docs/QUICK_START.md) - Fast setup guide

### Tool Guides
- [top_stacks_stokastic.md](docs/top_stacks_stokastic.md) - Top Stacks tool methodology
- [sims_tool_instructions.md](docs/sims_tool_instructions.md) - Lineup Simulator guide
- [review_sims_tool.md](docs/review_sims_tool.md) - Simulator review & improvements
- [ROO_README.md](docs/ROO_README.md) - ROO projections system

### Feature Documentation
- [boom_bust_tool.md](docs/boom_bust_tool.md) - Boom/Bust methodology
- [ceiling_floor_projections.md](docs/ceiling_floor_projections.md) - Projection calculations
- [ownership_projections.md](docs/ownership_projections.md) - Ownership modeling
- [weighted_opportunity.md](docs/weighted_opportunity.md) - Opportunity metrics

### Technical Details
- [DST_INTEGRATION.md](docs/DST_INTEGRATION.md) - Defense/Special Teams handling
- [NEW_DATA_STRUCTURE.md](docs/NEW_DATA_STRUCTURE.md) - Data pipeline overview
- [PIPELINE_SIMPLIFICATION.md](docs/PIPELINE_SIMPLIFICATION.md) - Pipeline improvements

### Change Logs
- [MODULARIZATION_SUMMARY.md](docs/MODULARIZATION_SUMMARY.md) - Code organization changes
- [OPTIMIZATION_SUMMARY.md](docs/OPTIMIZATION_SUMMARY.md) - Performance optimizations
- [sim_tool_improvements.md](docs/sim_tool_improvements.md) - Simulator enhancements

---

## 📦 Tools Included

### 1. **Top Stacks & Boom/Bust Tool**
**Pre-contest lineup builder with advanced boom/bust modeling**

**Access:** Via unified app → Select "⭐ Top Stacks & Boom/Bust"

**Features:**
- Correlation-aware NFL stack optimization
- Percentile-based boom thresholds (calibrated to winning scores)
- Position-specific boom targeting (QB, RB, WR, TE, DST)
- Defensive matchup adjustments with Z-scores
- Weighted scoring with boom probability emphasis
- Visual boom target analysis with conditional coloring
- PROE integration for pass-heavy game scripts
- Sharp Football metrics (EPA, Explosive%, PPD)

**Required Files:**
- roo_projections.csv (ROO simulator output)
- Matchup.csv (Vegas lines: ITT, Spread, Total)
- Weekly_Stats.csv (historical player stats)
- sharp_offense.csv (team offensive metrics)
- sharp_defense.csv (team defensive metrics)
- weekly_proe_2025.csv (Pass Rate Over Expected)

---

### 2. **DFS Lineup Simulator**
**Monte Carlo lineup validation against field competition**

**Access:** Via unified app → Select "📊 Lineup Simulator"

**Features:**
- Game environment modeling with pace and matchup factors
- Correlated player simulations
- Field lineup generation with ownership
- ROI analysis across thousands of scenarios
- Cash rate and top-finish probability calculations

---

### 3. **Pre-Contest Simulator**
**Optimize player pool and exposures BEFORE lineup lock**

**Access:** Via unified app → Select "🎲 Pre-Contest Simulator"

**Features:**
- Player pool ROI analysis
- Optimal exposure recommendations
- Boom/bust probability modeling
- Expected value calculations
- Risk-adjusted player rankings

---

### 4. **Ownership Adjuster**
**Adjust ownership projections to match DK roster construction**

**Access:** Via unified app → Select "🦃 Ownership Adjuster"

**Features:**
- Normalize ownership to 900% total (9 positions)
- FLEX position distribution control
- Before/after comparison
- CSV export for adjusted ownership

---

### 5. **Contest Analyzer**
**Post-contest analysis with 7 comprehensive analysis tabs**

**Access:** Via unified app → Select "🏆 Contest Analyzer"

**Features:**
- Ownership analysis and field distribution
- Leverage scoring (winners' edge identification)
- Stack construction analysis
- Personal performance tracking
- Boom/bust projection accuracy
- ROI and profit tracking with payout calculator
- Post-contest simulator (removes variance)

---

### 6. **ROO Simulator** (Data Generation)
**Generate Range-of-Outcomes projections with Monte Carlo simulation**

**Usage:** `python roo_simulator.py`

**Features:**
- 10,000 simulation Monte Carlo engine
- 8-week lookback for historical volatility calculation
- Matchup volatility multipliers (0.8-1.3) incorporating:
  - Sharp Football metrics (EPA, Explosive%, PPD)
  - PROE (Pass Rate Over Expected) with time weighting
  - Implied Team Totals
  - Opponent defensive quality
- Lognormal distributions for realistic scoring simulation
- Floor (15th percentile) and Ceiling (85th percentile) projections
- Volatility Index for player consistency measurement

**Output:**
- `roo_projections.csv` with 27 columns including Floor_Proj, Ceiling_Proj, OWS_Median_Proj, matchup_vol_multiplier, Volatility_Index

**Required Files:**
- Weekly_Stats.csv, Weekly_DST_Stats.csv
- Salaries_2025.csv, Matchup.csv
- sharp_offense.csv, sharp_defense.csv
- weekly_proe_2025.csv, projections_2025.csv

---

## 🔄 Complete DFS Workflow

```
1. DATA GENERATION:
   python roo_simulator.py → Generate ROO projections
   python weekly_proe.py → Update PROE data

2. PRE-CONTEST RESEARCH:
   streamlit run app.py
   ├── Top Stacks Tool → Research game stacks and boom candidates
   ├── Pre-Contest Simulator → Identify optimal player pool
   ├── Lineup Simulator → Test lineups against field competition
   └── Ownership Adjuster → Fine-tune ownership if needed

3. BUILD LINEUPS:
   Use insights + your optimizer → Generate lineups

4. POST-CONTEST ANALYSIS:
   streamlit run app.py → Contest Analyzer tab
   └── Learn from results, identify edges, improve process
```

---

## 🚀 Quick Start

### Installation

1. **Install dependencies:**
```bash
pip install streamlit pandas numpy plotly
```

2. **Navigate to the tools directory:**
```bash
cd c:\Users\schne\.vscode\.venv\dfsdude-tools
```

### Running the Unified App (Recommended)

**Single command to access all tools:**
```bash
streamlit run app.py
```

Or double-click: `launch_dfs_tools.bat`

---

## 📊 Complete DFS Workflow

```
1. DATA GENERATION:
   python roo_simulator.py → Generate ROO projections

2. PRE-CONTEST RESEARCH:
   Unified App → Pre-Contest Simulator → Identify optimal player pool
   Unified App → Top Stacks Tool → Research game stacks and boom candidates

3. BUILD LINEUPS:
   Use insights to build lineups in your optimizer

4. VALIDATE LINEUPS:
   Unified App → Lineup Simulator → Test against field competition
   Unified App → Ownership Adjuster → Fine-tune ownership if needed
   
5. POST-CONTEST ANALYSIS:
   streamlit run contest_analyzer.py → Learn from results
   
3. POST-CONTEST:
   Results + Projections → Contest Analyzer → Learn & improve
   Post-Contest Simulator → Identify good plays regardless of outcome
```

---

## 🎯 Key Concepts

### Sim ROI
**Expected ROI across thousands of simulations** - Removes variance to reveal true lineup/player quality
- **Post-contest**: See if you got lucky/unlucky
- **Pre-contest**: Optimize before submitting

### Stack Construction
- **Primary QB Stack**: QB + teammates (same team)
- **Bring-Back**: Opponent pass catchers in same game  
- **Secondary Game Stack**: 2+ players from different game

### Leverage
**Leverage Score** = (Player FPTS - avg) / (Own% + 1) - Identifies contrarian plays that paid off

---

**Version**: 1.0.0  
**Last Updated**: November 2025