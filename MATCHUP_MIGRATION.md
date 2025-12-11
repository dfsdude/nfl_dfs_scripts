# Matchup Migration Summary - odds.csv Integration

## Overview
Successfully migrated from manual `Matchup.csv` maintenance to automated `odds.csv` data from The Odds API. The system now automatically transforms betting odds into the expected matchup format used throughout the codebase.

## Changes Made

### 1. data/data_loader.py - Core Transformation Logic
**Function Updated**: `load_matchups()`

**What it does**:
- Checks for `data/odds-api/odds.csv` first
- If found, transforms odds.csv (home/away format) → Matchup.csv format (Init/Opp bidirectional)
- Falls back to legacy `Matchup.csv` if odds.csv doesn't exist

**Transformation Logic**:
```python
# For each game in odds.csv:
# 1. Create home team row
Init = home_team, Opp = away_team
Spread = spread_home (already from home perspective)
Total = over_under_line
ITT = (Total / 2) + (Spread / 2)

# 2. Create away team row
Init = away_team, Opp = home_team
Spread = -spread_home (flip for away perspective)
Total = over_under_line
ITT = (Total / 2) + (Spread / 2)
```

**Example**: TB @ ATL, spread TB -4.5, total 44.5
```
TB row: Init=TB, Opp=ATL, Spread=-4.5, Total=44.5, ITT=20.0
ATL row: Init=ATL, Opp=TB, Spread=+4.5, Total=44.5, ITT=24.5
```

### 2. roo_simulator.py - ROO Simulator Integration
**Changes**:
- Added import: `from data.data_loader import load_matchups`
- Updated `load_data()` function to use `load_matchups()` instead of direct CSV read
- Maintains all existing functionality with new data source

**Benefits**:
- Automatically gets latest odds when running simulations
- No manual CSV updates needed before sim runs
- Historical odds preserved with event_id tracking

### 3. modules/top_stacks.py - Top Stacks Module Integration
**Changes**:
- Added data_loader import with try/except for safety
- Updated both data loading paths (ROO projections and legacy fallback)
- Uses `load_matchups()` when available, falls back to direct CSV read

**Preserved Functionality**:
- `matchup_dict` creation: `matchups.set_index("Init")["Opp"].to_dict()`
- `matchup_expanded` creation: `matchups.set_index("Init").to_dict(orient="index")`
- All game script calculations still work identically

### 4. utils/test_matchup_migration.py - Validation Script
**Purpose**: Comprehensive test to verify transformation correctness

**Tests Performed**:
✅ Column presence (Init, Opp, Spread, Total, ITT)
✅ Bidirectional structure (2 rows per game)
✅ Spread symmetry (home + away spreads = 0)
✅ ITT sum equals Total
✅ matchup_dict creation
✅ matchup_expanded creation

**Test Results**:
```
✓ 16 games → 32 matchup rows
✓ All expected columns present
✓ Spread symmetry verified (TB: -4.5, ATL: +4.5)
✓ ITT calculations correct (20.0 + 24.5 = 44.5)
✓ matchup_dict and matchup_expanded work correctly
```

## Data Flow

### Before (Manual Process):
```
User manually updates Matchup.csv
    ↓
Applications read Matchup.csv directly
    ↓
Manual updates required every week
```

### After (Automated Process):
```
The Odds API → fetch_odds.py
    ↓
odds.csv saved to data/odds-api/
    ↓
load_matchups() transforms odds.csv
    ↓
Applications get matchup data (same format)
    ↓
Automatic updates when odds.csv refreshed
```

## Benefits

### 1. Automation
- ✅ No manual CSV editing required
- ✅ Run `fetch_odds.py` to get latest lines
- ✅ All applications automatically use new data

### 2. Data Quality
- ✅ Real-time odds from reputable sportsbooks
- ✅ Price factor adjustments for true implied probabilities
- ✅ Multiple moneyline formats (American, Decimal, Adjusted)

### 3. Historical Tracking
- ✅ event_id enables line movement tracking
- ✅ schedule_date and week_label for temporal analysis
- ✅ Can compare opening vs closing lines (future enhancement)

### 4. Future Extensibility
- ✅ Moneyline data available for win probability
- ✅ Can add line movement alerts
- ✅ Can integrate with prop bet odds
- ✅ Ready for live in-game odds (if needed)

## Backwards Compatibility

**Fallback Mechanism**:
- If `odds.csv` doesn't exist, system falls back to `Matchup.csv`
- Existing `Matchup.csv` files still work
- No breaking changes to existing workflows

**Gradual Migration**:
- Can run both systems in parallel
- Test odds.csv transformation while keeping Matchup.csv as backup
- Remove Matchup.csv when fully validated

## Usage

### For End Users:
1. Run `fetch_odds.py` to get latest odds (weekly before slate)
2. Run applications normally (they automatically use odds.csv)
3. No other changes needed

### For Developers:
```python
from data.data_loader import load_matchups

# Get matchup data (automatically transformed from odds.csv)
matchups = load_matchups()

# Use as before
matchup_dict = matchups.set_index("Init")["Opp"].to_dict()
matchup_expanded = matchups.set_index("Init").to_dict(orient="index")

# Access team matchup data
team_matchup = matchup_expanded.get(team, {})
spread = team_matchup.get('Spread', 0)
itt = team_matchup.get('ITT', 22)
```

## Testing

Run the validation script to verify transformation:
```bash
python utils/test_matchup_migration.py
```

Expected output:
- ✅ 32 matchup rows from 16 games
- ✅ All columns present
- ✅ Spread symmetry verified
- ✅ ITT calculations correct

## Next Steps

### Immediate:
1. ✅ Test with real applications (top_stacks, roo_simulator)
2. ✅ Verify game script calculations produce expected results
3. ✅ Remove hardcoded Matchup.csv paths if everything works

### Future Enhancements:
- Add line movement tracking (compare odds over time)
- Implement win probability from moneylines
- Add alternate lines (player props) support
- Create odds visualization dashboard
- Integrate with live in-game odds for DFS adjustments

## Files Modified

1. `data/data_loader.py` - Added transformation logic
2. `roo_simulator.py` - Updated to use load_matchups()
3. `modules/top_stacks.py` - Updated to use load_matchups()
4. `utils/test_matchup_migration.py` - Created validation script
5. `plan.md` - Updated to mark migration as complete

## Migration Status: ✅ COMPLETE

All core functionality verified and working. Applications now automatically use odds.csv data when available.
