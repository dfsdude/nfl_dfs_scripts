# DFS Tools Suite - Unified Application

## Overview
A unified Streamlit application that provides access to all DFS analysis tools from a single interface.

## Tools Included

### 1. Top Stacks & Boom/Bust Tool (⭐)
**Purpose**: Identify optimal game stacks and boom/bust candidates

**Features**:
- Game environment scoring with pace metrics
- PROE integration for pass-heavy game scripts  
- Stack recommendations (QB + Bring-Back combinations)
- Boom/Bust ratings with ceiling/floor projections
- Sharp Football metrics integration

**Use Case**: Pre-lineup construction research

---

### 2. Lineup Simulator (📊)
**Purpose**: Simulate your lineups against realistic field competition

**Features**:
- Monte Carlo simulation (10,000+ iterations)
- Game correlation modeling
- Field lineup generation with ownership
- ROI calculation and cash probability
- Top-finish probability analysis (Top 1%, Top 5%, etc.)

**Use Case**: Post-lineup construction validation

---

### 3. Pre-Contest Simulator (🎲)
**Purpose**: Optimize player pool and exposures BEFORE lineup lock

**Features**:
- ROO (Range of Outcomes) projections
- Exposure optimization recommendations
- Volatility analysis
- Player pool selection guidance
- Risk/reward profiling

**Use Case**: Player pool selection and exposure planning

---

### 4. Ownership Adjuster (🦃)
**Purpose**: Normalize ownership projections to DraftKings roster constraints

**Features**:
- Position-based normalization (1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX, 1 DST)
- Roster construction compliance
- Bulk ownership adjustments
- CSV import/export

**Use Case**: Ownership projection calibration

---

## How to Run

### Option 1: Unified App (Recommended)
Launch all tools from a single interface:

```powershell
cd c:\Users\schne\.vscode\.venv\dfsdude-tools
C:/Users/schne/.vscode/.venv/Scripts/streamlit.exe run app.py
```

Or simply:
```powershell
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\app.py
```

Navigate between tools using the sidebar menu.

### Option 2: Individual Tools (Standalone)
Each tool can still be run independently:

```powershell
# Top Stacks Tool
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\top_stacks_tool.py

# Lineup Simulator
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\sims_tool.py

# Pre-Contest Simulator
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\pre_contest_simulator.py

# Ownership Adjuster
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\ownership_adjuster.py
```

---

## Data Pipeline

### Required Data Files
All tools expect CSV files in:
```
C:\Users\schne\Documents\DFS\2025\Dashboard\
```

**Core Files**:
- `Salaries_2025.csv` - DraftKings player salaries
- `Weekly_Stats.csv` - Historical player performance (8 weeks)
- `Weekly_DST_Stats.csv` - Historical DST performance
- `Matchup.csv` - Vegas lines (ITT, Spread, Total, Location)
- `sharp_offense.csv` - Team offensive metrics (EPA, Explosive%, PPD)
- `sharp_defense.csv` - Team defensive metrics (EPA Allowed, etc.)
- `weekly_proe_2025.csv` - Pass Rate Over Expected by team/week
- `roo_projections.csv` - Output from ROO simulator

**Optional Files**:
- `Player_Mapping.csv` - Name standardization (1869 mappings)
- `projections_2025.csv` - Third-party projections for comparison

### Data Generation
Generate ROO projections first:
```powershell
python c:\Users\schne\.vscode\.venv\dfsdude-tools\roo_simulator.py
```

This creates `roo_projections.csv` with:
- Floor/Ceiling projections (15th/85th percentiles)
- Median projections
- Volatility Index
- Matchup volatility multipliers (incorporates PROE)

---

## Recommended Workflow

1. **Generate ROO Projections**
   ```bash
   python roo_simulator.py
   ```
   Creates `roo_projections.csv` with Monte Carlo-based player projections.

2. **Launch Unified App**
   ```bash
   streamlit run app.py
   ```

3. **Pre-Contest Research**
   - Use **Pre-Contest Simulator** to identify optimal player pool
   - Use **Top Stacks Tool** to research game environments and stacks

4. **Build Lineups**
   - Generate lineups in your optimizer using the insights

5. **Validate Lineups**
   - Use **Lineup Simulator** to test against field competition
   - Adjust ownership if needed with **Ownership Adjuster**

---

## Technical Architecture

### Module Structure
```
dfsdude-tools/
├── app.py                      # Main unified launcher
├── modules/                    # Modularized tools
│   ├── __init__.py
│   ├── top_stacks.py          # Top Stacks & Boom/Bust
│   ├── sims_tool.py           # Lineup Simulator
│   ├── pre_contest_sim.py     # Pre-Contest Simulator
│   └── ownership_adjuster.py  # Ownership Adjuster
├── top_stacks_tool.py         # Original standalone version
├── sims_tool.py               # Original standalone version
├── pre_contest_simulator.py   # Original standalone version
├── ownership_adjuster.py      # Original standalone version
└── roo_simulator.py           # Data generation script
```

### Modularization Approach
- Each tool wrapped in a `run()` function
- `st.set_page_config()` only in `app.py` (unified) or `if __name__ == "__main__"` (standalone)
- Maintains backward compatibility - original files still work independently
- Shared navigation sidebar in unified app

---

## Key Features

### PROE Integration
**Pass Rate Over Expected (PROE)** is integrated throughout:
- **Top Stacks**: Position-specific bonuses (QB/WR get +12 pts for PROE ≥8%)
- **ROO Simulator**: Time-weighted PROE affects volatility multipliers
  - Pass-heavy teams → higher volatility (more boom/bust)
  - Run-heavy teams → lower volatility (more consistent)
  - Recent weeks weighted more heavily (0.85 decay per week)

### Sharp Football Metrics
- **EPA/Play**: Expected Points Added per play
- **Explosive Play Rate**: % of plays gaining 20+ yards
- **Points Per Drive**: Team scoring efficiency
- **Down Conversion Rate**: 3rd/4th down success rate

All metrics available for both offense and defense.

### Matchup Volatility Multiplier
ROO simulator calculates 0.8-1.3 multiplier based on:
- Team offensive strength (EPA, Explosive%, PPD)
- Opponent defensive weakness (EPA Allowed, Explosive% Allowed, PPD Allowed)
- Implied Team Total (Vegas expectation)
- PROE (pass-heavy tendencies increase volatility)

---

## Configuration

### ROO Simulator Settings
Located in `roo_simulator.py`:
```python
N_SIMULATIONS = 10000      # Monte Carlo iterations
LOOKBACK_WEEKS = 8         # Historical data window
MIN_GAMES_FOR_PLAYER = 4   # Minimum games for volatility calc
FLOOR_PERCENTILE = 15      # Floor = 15th percentile
CEILING_PERCENTILE = 85    # Ceiling = 85th percentile
MATCHUP_VOL_MIN = 0.8      # Min volatility multiplier
MATCHUP_VOL_MAX = 1.3      # Max volatility multiplier
```

### Data Paths
Update in each tool if needed:
```python
DATA_DIR = Path(r"C:\Users\schne\Documents\DFS\2025\Dashboard")
```

---

## Troubleshooting

### "File does not exist" errors
Ensure all required CSV files are in:
```
C:\Users\schne\Documents\DFS\2025\Dashboard\
```

### "No st.set_page_config" warning
This is normal when tools are run through the unified app (config set in `app.py`).

### Team name mismatches
Tools use mapping dictionary:
```python
abbrev_to_full = {
    'BUF': 'Bills', 'KC': 'Chiefs', 'SF': '49ers', ...
}
```
Salaries/Matchups use abbreviations; Sharp Football uses full names.

### Missing player volatility
ROO simulator requires 4+ games in lookback window. New players get position defaults:
- QB: 5.5, RB: 5.0, WR: 5.0, TE: 4.5, DST: 3.0

---

## Future Enhancements
- [ ] Add export functionality to save research across tools
- [ ] Integrate optimizer directly into unified app
- [ ] Add historical slate analysis
- [ ] Create lineup generation within Pre-Contest Simulator
- [ ] Add real-time ownership tracking during contests

---

## Support
For issues or questions, refer to individual tool documentation:
- `ROO_README.md` - ROO Simulator details
- `boom_bust_tool.md` - Top Stacks methodology
- `sims_tool_instructions.md` - Lineup Simulator guide

---

**Built with**: Streamlit, Pandas, NumPy, Plotly
**Data Sources**: Sharp Football Analytics, nflverse (PROE), DraftKings
