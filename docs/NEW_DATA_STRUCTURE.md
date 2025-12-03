# New Data Structure - DFS Boom/Bust Tool

## Overview
The tool has been reconfigured to use a cleaner, more efficient data structure with pre-calculated metrics and industry-standard Sharp analytics (EPA-based).

## Required Input Files

### 1. **ows_projections.csv** (Current Week Projections & Ownership)
Weekly player projections and ownership percentages from your projection source.

**Required Columns:**
- `Id`: DraftKings player ID (must match Salaries_2025.csv)
- `Name`: Player name
- `Position`: QB, RB, WR, TE, DST
- `ProjPts`: Projected DraftKings points
- `ProjOwn`: Projected ownership percentage (as whole number, e.g., 6.31 = 6.31%)

**Example:**
```
Id,Name,Position,Team,ProjPts,ProjOwn
40926067,Los Angeles Chargers,DST,Chargers,11.44,6.31
40925485,Keenan Allen,WR,Chargers,11.22,6.54
40925517,Jerry Jeudy,WR,Browns,7.65,0
```

**Usage:**
- **Primary projection source**: Tool uses `ProjPts` as median projection
- **Ownership data**: `ProjOwn` converted to decimal (6.31 → 0.0631)
- Merged with Salaries_2025.csv using `Id` field for exact matching

---

### 2. **Matchup.csv** (Simplified Game Data)
Core game information without embedded team metrics.

**Required Columns:**
- `Game`: Game identifier (e.g., "PHI@DAL")
- `Init`: Initiating team (team being analyzed)
- `ITT`: Implied Team Total (expected points)
- `Loc`: Location ("Home" or "Away")
- `FavStatus`: Favorite status indicator
- `Opp`: Opponent team abbreviation
- `Opp_ITT`: Opponent's Implied Team Total
- `OppStatus`: Opponent status indicator
- `Total`: Game total (over/under)
- `Spread`: Point spread (negative = favorite, e.g., -7 = 7-point favorite)

**Example:**
```
Game,Init,ITT,Loc,FavStatus,Opp,Opp_ITT,OppStatus,Total,Spread
PHI@DAL,PHI,24.5,Away,Underdog,DAL,27.5,Favorite,52,-3.0
```

---

### 3. **Weekly_Stats.csv** (Historical Offensive Stats)
Week-by-week player performance with pre-calculated weighted opportunities.

**Required Columns:**
- `Player`: Player name
- `Position`: QB, RB, WR, TE, DST
- `Week`: Week number
- `Team`: Team abbreviation
- `Opp`: Opponent team abbreviation
- `Targets`: Receiving targets (WR/TE)
- `Receptions`: Receptions
- `Rec_TD`: Receiving touchdowns
- `Rec_Yds`: Receiving yards
- `Rush_Att`: Rush attempts
- `Rush_Yds`: Rushing yards
- `Rush_TD`: Rushing touchdowns
- `Pass_Att`: Pass attempts (QB)
- `Pass_Comp`: Pass completions (QB)
- `Pass_Yds`: Passing yards (QB)
- `Pass_TD`: Passing touchdowns (QB)
- `Passer_Rating`: QB passer rating
- **`Weighted_Opportunities`**: Pre-calculated weighted usage metric (RBs)
- `Int`: Interceptions thrown (QB)
- `Fumble_Lost`: Fumbles lost
- `DK_Points`: DraftKings points scored

**Usage:**
- Tool aggregates last 4 weeks to calculate **ceiling** (max DK_Points) and **variance** (std of DK_Points)
- **Projections** come from ows_projections.csv (not Weekly_Stats averages)
- RB volume bonuses based on `Weighted_Opportunities` (18+ = elite, 15-18 = high, 12-15 = moderate)

---

### 4. **Weekly_DST_Stats.csv** (Historical DST Stats)
Defense/Special Teams performance by week.

**Required Columns:**
- `Player`: DST name (e.g., "Eagles DST")
- `Team`: Team abbreviation
- `Week`: Week number
- `Opp`: Opponent team abbreviation
- `Fum`: Fumble recoveries
- `DST_TD`: Defensive/ST touchdowns
- `Int`: Interceptions
- `SACK`: Sacks
- `Safety`: Safeties
- `Points_Against`: Points allowed
- `DK_Points`: DraftKings points scored

---

### 5. **sharp_offense.csv** (Team Offensive Metrics)
Team-level offensive efficiency metrics (EPA-based).

**Required Columns:**
- `Team`: Team abbreviation
- `EPA_Play`: Expected Points Added per play
- `Yards Per Play`: Average yards per play
- `Points Per Drive`: Average points per drive
- `Explosive Play Rate`: Rate of explosive plays (20+ yd gains)
- `Down Conversion Rate`: 3rd/4th down conversion rate

**Usage:**
- Provides context for game environment and team quality
- Used in team offense dictionary for stack analysis

---

### 6. **sharp_defense.csv** (Team Defensive Metrics)
Team-level defensive efficiency metrics (EPA-based).

**Required Columns:**
- `Team`: Team abbreviation (defender)
- `EPA_Play_Allowed`: Expected Points Added per play allowed
- `Yards Per Play Allowed`: Average yards per play allowed
- `Points Per Drive Allowed`: Average points per drive allowed
- `Explosive Play Rate Allowed`: Rate of explosive plays allowed
- `Down Conversion Rate Allowed`: 3rd/4th down conversion rate allowed

**Usage:**
- **Critical for matchup adjustments**: Higher EPA_Play_Allowed = weaker defense (boosts offensive projections)
- Replaces old z-score defensive strength calculations
- EPA scaling: ~0.1 EPA difference = ~10% projection adjustment
- Bounded adjustments: 0.8x to 1.2x (prevents extreme values)

---

### 7. **Salaries_2025.csv** (DraftKings Salary History)
Historical and current week salary data.

**Required Columns:**
- `Position`: QB, RB, WR, TE, DST
- `Name + ID`: Combined name/ID field
- `Name`: Player name
- `ID`: DraftKings player ID
- `Roster Position`: Roster slot
- `Salary`: DraftKings salary
- `Game Info`: Game information string
- `TeamAbbrev`: Team abbreviation
- `AvgPointsPerGame`: Season average DK points
- `Week`: Week number

**Usage:**
- Tool uses `Week` column max to identify current week
- Merges current week salaries with ows_projections.csv via `ID` field
- Historical salary data available for trend analysis
- `AvgPointsPerGame` used as fallback if projections missing

---

## Key Changes from Old Structure

### What Was Replaced:
1. ❌ **Players.csv** → Now built from ows_projections.csv + Weekly_Stats + Salaries
2. ❌ **Team_Plays_Offense.csv** → Replaced by sharp_offense.csv (EPA-based)
3. ❌ **Team_Plays_Defense.csv** → Replaced by sharp_defense.csv (EPA-based)
4. ❌ **Weighted Z-Score Allowed.csv** → Replaced by EPA_Play_Allowed
5. ❌ **Complex Matchup.csv** → Simplified to game data only

### What Was Added:
1. ✅ **ows_projections.csv** → PRIMARY projection & ownership source
2. ✅ **Weekly_Stats.csv** → Ceiling/variance + weighted opportunities
3. ✅ **Weekly_DST_Stats.csv** → Dedicated DST stats
4. ✅ **sharp_offense.csv** → EPA offensive metrics
5. ✅ **sharp_defense.csv** → EPA defensive metrics
6. ✅ **Salaries_2025.csv** → Salary tracking (ID matching)

### Benefits:
- ✅ **Trusted projections**: Use your own ows_projections.csv source
- ✅ **Real ownership data**: Actual ProjOwn percentages (not defaults)
- ✅ **Historical ceiling/variance**: From Weekly_Stats recent performance
- ✅ **Pre-calculated WO**: Weighted_Opportunities ready to use
- ✅ **EPA matchup adjustments**: More accurate than z-scores
- ✅ **Clean data separation**: Dedicated files by data type
- ✅ **ID-based merging**: Exact player matching via DK IDs

---

## Configuration Updates

### New Constants (DFSConfig class):
```python
EPA_FACTOR_MIN = 0.8   # Max penalty for tough matchup (was 0.5 for z-score)
EPA_FACTOR_MAX = 1.2   # Max boost for great matchup (was 1.5 for z-score)
```

### New Required Columns:
```python
REQUIRED_MATCHUP_COLS = ["Init", "Opp", "ITT", "Loc", "FavStatus", "Spread"]
REQUIRED_WEEKLY_STATS_COLS = ["Player", "Position", "Team", "Weighted_Opportunities"]
REQUIRED_SALARY_COLS = ["Name", "TeamAbbrev", "Salary", "Position"]
REQUIRED_PROJECTIONS_COLS = ["Id", "Name", "Position", "ProjPts", "ProjOwn"]
```

---

## Player Ranking Enhancements

### New RB Volume Bonus (uses Weighted_Opportunities):
- **Elite Volume** (18+ WO/G): +15 points to Player_Rank
- **High Volume** (15-17.9 WO/G): +10 points
- **Moderate Volume** (12-14.9 WO/G): +5 points

### Existing Bonuses (unchanged):
- **WR Variance Bonus**: +10 for high variance + high ceiling + ≤10% owned
- **RB Game Script Bonus**: +5/+8/+12 for home favorites by spread tier
- **QB Game Script Bonus**: +5/+10/+15 for scoring environment + value pricing combos

---

## Ownership Projection Note

✅ **RESOLVED**: Ownership now comes from `ows_projections.csv`!

The tool uses the `ProjOwn` column from ows_projections.csv for all ownership percentages. Values are automatically converted from whole numbers to decimals (e.g., 6.31% → 0.0631).

**No additional ownership file needed** - it's integrated in your projections file.

---

## Migration Checklist

- [ ] Obtain **ows_projections.csv** with current week ProjPts and ProjOwn
- [ ] Obtain Weekly_Stats.csv with pre-calculated Weighted_Opportunities
- [ ] Obtain Weekly_DST_Stats.csv with historical DST performance
- [ ] Obtain sharp_offense.csv with EPA-based team metrics
- [ ] Obtain sharp_defense.csv with EPA-based defensive metrics
- [ ] Update Salaries_2025.csv with current week data
- [ ] Ensure `ID` field in Salaries matches `Id` in ows_projections.csv
- [ ] Simplify Matchup.csv to required columns only
- [ ] Verify team abbreviations are consistent across all files
- [ ] Verify player names match between Weekly_Stats and ows_projections.csv
- [ ] Test with actual data to validate merges work correctly

---

## Technical Notes

### Data Loading Process:
1. Load all 7 CSV files
2. Identify current week from Salaries max(Week)
3. Merge current week salaries with ows_projections.csv (via ID field)
4. Aggregate Weekly_Stats (last 4 weeks) → ceiling (max), variance (std)
5. Merge historical stats with salaries+projections
6. Map opponent, spread, ITT, home/away from Matchup.csv
7. Merge Sharp defensive EPA for matchup adjustments
8. Calculate EPA-based matchup_factor (0.8x to 1.2x range)
9. Adjust projections: proj_adj = proj × matchup_factor
10. Convert ownership: ProjOwn / 100 (6.31 → 0.0631)

### EPA Matchup Logic:
```python
# EPA_Play_Allowed: Higher = worse defense (good for offense)
# 0 EPA = neutral (1.0x multiplier)
# +0.1 EPA = ~10% projection boost
# -0.1 EPA = ~10% projection penalty
matchup_factor = (1 + epa_defense * 1.0).clip(0.8, 1.2)
```

### Fallback Handling:
- If Weekly_Stats missing for player → ceiling = proj × 1.5, variance = proj × 0.5
- If ows_projections missing for player → uses AvgPointsPerGame from Salaries
- If Weighted_Opportunities missing → defaults to 0 (no volume bonus)
- Ownership comes from ProjOwn (no defaults needed)

---

## Questions or Issues?

If you encounter data validation errors, check:
1. Column names match exactly (case-sensitive)
2. Team abbreviations consistent across files
3. Player names match between Weekly_Stats and Salaries
4. Week numbers align properly
5. No missing required columns

The tool will display specific validation errors on startup if data files are malformed.
