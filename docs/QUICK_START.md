# DFS Tools Suite - Quick Reference

## 🚀 Launch Commands

### Unified App (All Tools in One)
```bash
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\app.py
```
**OR** double-click: `launch_dfs_tools.bat`

### Individual Tools
```bash
# Generate projections
python c:\Users\schne\.vscode\.venv\dfsdude-tools\roo_simulator.py

# Top Stacks & Boom/Bust
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\top_stacks_tool.py

# Lineup Simulator
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\sims_tool.py

# Pre-Contest Simulator
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\pre_contest_simulator.py

# Ownership Adjuster
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\ownership_adjuster.py

# Contest Analyzer
streamlit run c:\Users\schne\.vscode\.venv\dfsdude-tools\contest_analyzer.py
```

---

## 📁 Data Files Location

All tools expect data in:
```
C:\Users\schne\Documents\DFS\2025\Dashboard\
```

### Core Files
| File | Purpose |
|------|---------|
| `Salaries_2025.csv` | DraftKings salaries (current week) |
| `Weekly_Stats.csv` | Player stats (8-week history) |
| `Weekly_DST_Stats.csv` | DST stats (8-week history) |
| `Matchup.csv` | Vegas lines (ITT, Spread, Total) |
| `sharp_offense.csv` | Team offense metrics |
| `sharp_defense.csv` | Team defense metrics |
| `weekly_proe_2025.csv` | Pass Rate Over Expected |
| `roo_projections.csv` | ROO simulator output (GENERATED) |

---

## 🔄 Typical Workflow

### Step 1: Generate Projections (Monday-Wednesday)
```bash
python roo_simulator.py
```
**Output**: `roo_projections.csv` with Floor/Ceiling/Volatility

### Step 2: Research (Thursday-Friday)
```bash
streamlit run app.py
```
1. **Pre-Contest Simulator**: Identify optimal player pool & exposures
2. **Top Stacks Tool**: Research game environments & boom candidates

### Step 3: Build Lineups (Friday-Saturday)
Use your optimizer with insights from Steps 1-2

### Step 4: Validate (Before Lock)
**Unified App → Lineup Simulator**
- Upload your lineups
- Simulate vs field
- Check ROI & cash probability

### Step 5: Analyze (Post-Contest)
```bash
streamlit run contest_analyzer.py
```
- Review winning lineups
- Analyze stack construction
- Calculate actual ROI
- Learn for next week

---

## 🎯 Tool Selection Guide

| Need | Tool |
|------|------|
| Generate projections | ROO Simulator |
| Find optimal stacks | Top Stacks Tool |
| Identify boom candidates | Top Stacks Tool |
| Optimize player exposures | Pre-Contest Simulator |
| Test lineups vs field | Lineup Simulator |
| Fix ownership numbers | Ownership Adjuster |
| Post-contest learning | Contest Analyzer |

---

## 🔧 Key Features by Tool

### ROO Simulator
- 10k simulations per player
- PROE-adjusted volatility (pass-heavy = more volatile)
- 8-week lookback for consistency
- Matchup multipliers (0.8-1.3)

### Top Stacks Tool
- 3 views: Player Boom/Bust | Top Stacks | Game Matchups
- Correlation modeling (QB-WR, WR-WR)
- PROE bonuses (+12 pts for high pass rate)
- Sharp Football integration

### Lineup Simulator
- Simulates entire slate with correlations
- Field generation based on ownership
- ROI + cash % + top finish %
- Lineup comparison table

### Pre-Contest Simulator
- Player ROI ranking
- Exposure recommendations
- Portfolio expected value
- Interactive exposure editor

### Ownership Adjuster
- Position normalization (1/2/3/1/1/1)
- Preserves relative ownership
- Visual ownership charts
- CSV import/export

---

## 💡 Pro Tips

1. **Always run ROO simulator first** - other tools depend on `roo_projections.csv`

2. **Use unified app for efficiency** - no need to launch multiple tools separately

3. **Check matchup volatility multipliers** - tells you which games are more unpredictable
   - 0.8 = run-heavy, low-scoring grind
   - 1.3 = pass-heavy, high-variance shootout

4. **PROE matters** - teams with PROE ≥8% get major boom bonuses
   - Positive PROE = pass-heavy = more boom/bust
   - Negative PROE = run-heavy = consistent but capped

5. **Simulate before submitting** - Lineup Simulator catches bad lineups early

6. **Trust the optimizer exposures** - Pre-Contest Simulator finds +EV plays

7. **Learn from winners** - Contest Analyzer shows what worked

---

## 🐛 Common Issues

### "File not found"
→ Check data path: `C:\Users\schne\Documents\DFS\2025\Dashboard\`

### "Page config error"
→ Use unified app (`app.py`) to avoid conflicts

### "Team name not found"
→ Tools map abbreviations (BUF) to full names (Bills) automatically

### "Missing player volatility"
→ Need 4+ games in history; new players get position defaults

### "Matchup multiplier stuck at 0.8"
→ Was fixed by adding team name mapping in roo_simulator.py

---

## 📊 Key Metrics Explained

### Boom %
Probability of hitting 4× salary value (DFS tournament winning threshold)

### Volatility Index
Higher = more inconsistent (boom/bust), Lower = more stable (cash game)

### Leverage
Your ownership advantage over field (want high on winners)

### ROI (Return on Investment)
Expected profit per dollar entered (100% = double your money)

### Matchup Vol Multiplier
How much variance the specific matchup adds (0.8-1.3 range)

### PROE (Pass Rate Over Expected)
+0.10 = 10% more passes than expected (pass-heavy game script)
-0.10 = 10% fewer passes than expected (run-heavy game script)

---

## 📖 Documentation

| File | Content |
|------|---------|
| `UNIFIED_APP.md` | Complete unified app documentation |
| `ROO_README.md` | ROO Simulator deep dive |
| `boom_bust_tool.md` | Top Stacks methodology |
| `sims_tool_instructions.md` | Lineup Simulator guide |
| `README.md` | Main overview (this file) |

---

**Last Updated**: December 2, 2025
**Version**: 2.0 (Unified App Release)
