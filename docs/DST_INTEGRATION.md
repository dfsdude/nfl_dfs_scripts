# DST Integration for ROO Simulator

## Changes Made

Added support for Defense/Special Teams (DST) historical volatility calculation in `roo_simulator.py`.

### Files Updated
- `roo_simulator.py` - Added Weekly_DST_Stats.csv loading and DST volatility processing

## Implementation Details

### 1. Data Loading (`load_data()`)
**Added**: `weekly_dst_stats` to data dictionary
```python
data = {
    'weekly_stats': pd.read_csv(data_dir / "Weekly_Stats.csv"),
    'weekly_dst_stats': pd.read_csv(data_dir / "Weekly_DST_Stats.csv"),  # NEW
    'matchups': pd.read_csv(data_dir / "Matchup.csv"),
    # ... other files
}
```

### 2. Volatility Calculation (`build_player_volatility()`)
**Updated signature**: Now accepts both player and DST data
```python
def build_player_volatility(weekly_stats: pd.DataFrame, weekly_dst_stats: pd.DataFrame)
```

**Processing logic**:
1. **Offensive players**: Process Weekly_Stats.csv (QB/RB/WR/TE)
   - Group by `['Player', 'Team', 'Position']`
   - Calculate count, mean, std, min, max of `DK_Points`

2. **DST units**: Process Weekly_DST_Stats.csv separately
   - Group by `['Player', 'Team']` (Player = team name like "49ers")
   - Calculate same statistics
   - Assign `Position = 'DST'`

3. **Combine**: Concatenate offensive players and DST into single DataFrame

4. **Position averages**: Calculate for all positions including DST
   - Used as fallback for low-sample players
   - DST gets its own position-level std/mean

5. **Effective std calculation**: Same logic applies to DST
   - If ≥4 games: use player-specific std
   - If 2-3 games: blend player std with DST position avg
   - If <2 games: use DST position std × 1.2

### 3. Pipeline Integration (`generate_roo_projections()`)
**Updated function call**:
```python
player_volatility = build_player_volatility(data['weekly_stats'], data['weekly_dst_stats'])
```

## Weekly_DST_Stats.csv Schema

| Column | Type | Description |
|--------|------|-------------|
| Player | str | Team name (e.g., "49ers", "Bears") |
| Team | str | Team abbreviation (e.g., "SF", "CHI") |
| Week | int | Week number (1-18) |
| Opp | str | Opponent team abbreviation |
| Fum | int | Fumble recoveries |
| DST_TD | int | Defensive/Special teams touchdowns |
| Int | int | Interceptions |
| SACK | int | Sacks |
| Safety | int | Safeties |
| Points_Against | int | Points allowed |
| DK_Points | float | **DraftKings fantasy points** |

**Key field**: `DK_Points` - Used for volatility calculation (mean, std, min, max)

## Output Impact

DST units now included in `roo_projections.csv`:
- **Position**: "DST"
- **Player**: Team name (matches DK salaries convention)
- **Volatility metrics**: hist_games, hist_mean_fpts, hist_std_fpts, effective_std_fpts
- **Simulated ranges**: Floor_Proj (P15), Ceiling_Proj (P85), full percentile suite
- **Sharp metrics**: Defensive EPA, Explosive Play Rate Allowed, Points Per Drive Allowed

## Benefits

### ✅ Complete Slate Coverage
- Now simulates **all** DraftKings positions (QB, RB, WR, TE, DST)
- DST projections get same Monte Carlo treatment as offensive players

### ✅ DST Volatility Modeling
- Historical volatility from actual game performance
- Position-level fallbacks for low-sample DST units
- Matchup adjustments via opponent offensive metrics

### ✅ Boom/Bust for DST
- `top_stacks_tool.py` can now calculate boom/bust probabilities for DST
- Exposure recommendations for DST based on Player_Rank
- Stack analysis includes DST (useful for game stacks)

## Example DST Data

```csv
Player,Team,Week,Opp,Fum,DST_TD,Int,SACK,Safety,Points_Against,DK_Points
49ers,SF,1,SEA,2,0,0,1,0,13,5
Bears,CHI,1,MIN,0,1,1,3,0,27,11
Bengals,CIN,1,CLE,0,0,2,2,0,16,6
```

- **49ers**: 5 DK points (2 fumbles, 1 sack, 13 pts allowed)
- **Bears**: 11 DK points (1 TD, 1 INT, 3 sacks, 27 pts allowed)
- **Bengals**: 6 DK points (2 INTs, 2 sacks, 16 pts allowed)

## Validation

### Check DST in output
```python
import pandas as pd
from pathlib import Path

roo = pd.read_csv(Path(r"C:\Users\schne\Documents\DFS\2025\Dashboard\roo_projections.csv"))

# Filter to DST only
dst_projections = roo[roo['Position'] == 'DST']

print(f"DST units: {len(dst_projections)}")
print("\nSample DST projection:")
print(dst_projections.iloc[0])

# Check volatility metrics
print(f"\nDST with 4+ historical games: {(dst_projections['hist_games'] >= 4).sum()}")
print(f"Avg DST ceiling: {dst_projections['Ceiling_Proj'].mean():.1f}")
print(f"Avg DST floor: {dst_projections['Floor_Proj'].mean():.1f}")
```

### Console Output
When running `roo_simulator.py`, you should see:
```
Loading data files...
✓ Loaded 3200 historical player-game records
✓ Loaded 416 historical DST-game records  <-- NEW
✓ Loaded 216 current week projections

Calculating historical volatility...
  Using weeks 6 to 13 (8 weeks)
✓ Calculated volatility for 106 players (including DST)  <-- UPDATED
  Players with 4+ games: 74
  DST units: 32  <-- NEW
```

## Troubleshooting

### "FileNotFoundError: Weekly_DST_Stats.csv"
- Ensure file exists in `DATA_DIR` (default: `C:\Users\schne\Documents\DFS\2025\Dashboard`)
- Verify file name matches exactly (case-sensitive on some systems)

### "KeyError: 'DK_Points'" in DST processing
- Check Weekly_DST_Stats.csv has `DK_Points` column
- Verify CSV is properly formatted (commas, no extra quotes)

### DST not appearing in output
- Check that DST have projections in `ows_projections.csv`
- Verify DST have salaries in `Salaries_2025.csv` for current week
- Confirm Position = "DST" or "D" in projection files

### DST volatility looks strange
- Verify Week numbers in Weekly_DST_Stats.csv are correct
- Check that Team abbreviations match between files (SF vs SFO, etc.)
- Ensure DK_Points are reasonable (typically 0-20 range)

## Next Steps

### Optional Enhancements
1. **DST-specific matchup adjustments**: Consider opponent passing rate, turnover rate
2. **Streaming DST detection**: Flag low-cost DST with favorable matchups
3. **Game script impact**: Model DST scoring correlation with spread/ITT
4. **Blowout scenarios**: DST benefits from large leads (garbage time vs opponent)

### Integration with top_stacks_tool.py
The refactored `top_stacks_tool.py` now automatically includes DST:
- Loads DST from `roo_projections.csv`
- Calculates boom/bust probabilities (bust = <2pts, boom = >12pts typical)
- Generates exposure recommendations
- No additional changes needed!

---

**Summary**: `roo_simulator.py` now fully supports DST volatility modeling via Weekly_DST_Stats.csv. DST units are processed alongside offensive players, receive same Monte Carlo treatment, and appear in final ROO output with floor/ceiling projections.
