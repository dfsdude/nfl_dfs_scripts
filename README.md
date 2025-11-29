# 🏈 DFS Dude Tools

A complete suite of DFS (Daily Fantasy Sports) optimization and analysis tools for NFL contests.

## 📦 Tools Included

### 1. **Top Stacks Tool** (`top_stacks_tool.py`)
**Pre-contest lineup builder with advanced boom/bust modeling**

**Features:**
- Correlation-aware NFL stack optimization
- Percentile-based boom thresholds (calibrated to winning scores)
- Position-specific boom targeting (QB, RB, WR, TE, DST)
- Defensive matchup adjustments with Z-scores
- Weighted scoring with boom probability emphasis
- Visual boom target analysis with conditional coloring

**Usage:**
```bash
streamlit run top_stacks_tool.py
```

**Required Files:**
- Players.csv (salaries, positions, projections)
- Matchup.csv (opponent matchups)
- Team_stats.csv (offensive/defensive metrics)
- Weighted_z_scores.csv (defensive rankings)

---

### 2. **Contest Analyzer** (`contest_analyzer.py`)
**Post-contest analysis tool with 7 comprehensive tabs**

**Features:**

**Tab 1 - Ownership Analysis:**
- Field ownership distribution
- Top scorer analysis
- Interactive ownership vs performance scatter plots

**Tab 2 - Leverage Report:**
- Leverage score calculations (FPTS - avg) / (Own% + 1)
- Winners' edge players
- Optimal leverage identification

**Tab 3 - Stack Analysis:**
- QB stack distribution (QB+0, QB+1, QB+2, QB+3)
- Bring-back detection (opponent pass catchers)
- Secondary game stack analysis (2+ players from different game)
- FLEX position distribution
- Your stack construction vs winners comparison

**Tab 4 - My Performance:**
- Summary metrics (total entries, best finish, percentile)
- Lineup results breakdown
- Player overlap with winners

**Tab 5 - Boom/Bust Accuracy:**
- Projection vs actual performance
- Hit rate for high boom% plays
- Interactive accuracy scatter plots

**Tab 6 - ROI Tracker:**
- Full payout structure ($4000 1st → $20 for 416-1046)
- Entry-by-entry profit/loss
- Cash rate, break-even analysis
- Net profit calculations

**Tab 7 - Post-Contest Simulator:**
- **Monte Carlo simulations** to remove variance
- **Sim Lineup ROI** - true lineup quality across thousands of scenarios
- **Sim Player ROI** - which players were objectively good/bad plays
- Portfolio analysis vs field
- Identifies lucky/unlucky outcomes

**Usage:**
```bash
streamlit run contest_analyzer.py
```

**Required Files:**
- Player Ownership CSV (name, Own%, FPTS, position, Salary)
- Contest Top 0.1% CSV (Rank, EntryId, EntryName, Points, Lineup)
- My Entries CSV (Rank, EntryId, EntryName, Points, Lineup)
- Boom/Bust Projections CSV (name, Boom%, proj_adj, ceiling_adj, stddev_adj, Own%, team, opp)

---

### 3. **Pre-Contest Simulator** (`pre_contest_simulator.py`)
**Optimize player exposures BEFORE lineup lock**

**Features:**
- **Monte Carlo simulation** with your projection distributions
- **Player Sim ROI analysis** - which players project best ROI
- **Exposure optimization** - suggested % for each player
- **Portfolio evaluation** - expected ROI before submitting
- **Interactive exposure editor** by position
- Exposure presets (equal weight, projection-based, ownership-based)
- Field simulation using ownership projections
- Downloadable optimization reports

**Usage:**
```bash
streamlit run pre_contest_simulator.py
```

**Required Files:**
- Player Projections CSV (name, position, salary, team, opp, proj_adj, ceiling_adj, stddev_adj, Own%)

**Workflow:**
1. Upload projections file
2. Set contest settings (size, entry fee, # of lineups)
3. Configure target exposures for each player
4. Run simulation (1000-5000 iterations)
5. Review Player Sim ROI results
6. Adjust exposures based on recommendations
7. Export optimized exposures
8. Use exposures in your lineup builder

---

## 🚀 Quick Start

### Installation

1. **Install dependencies:**
```bash
pip install streamlit pandas numpy plotly
```

2. **Navigate to the tools directory:**
```bash
cd dfsdude-tools
```

### Running the Tools

**Pre-Contest Workflow:**
```bash
# Step 1: Build optimized stacks
streamlit run top_stacks_tool.py

# Step 2: Optimize exposures with simulation
streamlit run pre_contest_simulator.py
```

**Post-Contest Workflow:**
```bash
# Analyze results and learn from performance
streamlit run contest_analyzer.py
```

---

## 📊 Complete DFS Workflow

```
1. PRE-CONTEST:
   Projections → Top Stacks Tool → Generate stacks
   Projections → Pre-Contest Simulator → Optimize exposures
   
2. BUILD LINEUPS:
   Use optimized exposures in your lineup builder
   
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