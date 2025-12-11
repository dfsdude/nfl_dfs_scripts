# Quick Start: Using odds.csv with DFS Tools

## Overview
The DFS Tools Suite now automatically uses live betting odds from The Odds API instead of manually-maintained Matchup.csv files.

## Weekly Workflow

### Step 1: Fetch Latest Odds (Tuesday/Wednesday)
```bash
cd utils
python fetch_odds.py
```

**What it does**:
- Fetches current week's odds from The Odds API
- Saves to `data/odds-api/odds.csv`
- Shows 16 games with spreads, totals, moneylines

**Output**:
```
Saved week 15 odds to odds.csv (16 games)
API Requests remaining: 485/500
```

### Step 2: Run Applications (No Changes Needed!)
```bash
# ROO Simulator
python roo_simulator.py

# Top Stacks Analyzer  
streamlit run app.py
```

**What happens**:
- Applications call `load_matchups()` from `data/data_loader.py`
- System automatically transforms `odds.csv` → `Matchup.csv` format
- All calculations use latest odds (no manual CSV editing)

## Data Transformation (Automatic)

### Input: odds.csv (home/away format)
```csv
home_team,away_team,spread_home,spread_away,over_under_line
TB,ATL,-4.5,4.5,44.5
CHI,CLE,-7.5,7.5,38.5
```

### Output: Matchup format (Init/Opp bidirectional)
```
Init Opp  Spread Total  ITT
TB   ATL  -4.5   44.5   20.0
ATL  TB   +4.5   44.5   24.5
CHI  CLE  -7.5   38.5   15.5
CLE  CHI  +7.5   38.5   23.0
```

**Transformation Rules**:
- 1 game → 2 rows (home perspective + away perspective)
- Spread flips sign for away team
- ITT = (Total/2) + (Spread/2)
- Example: TB favored by 4.5, total 44.5
  - TB ITT: 22.25 - 2.25 = 20.0
  - ATL ITT: 22.25 + 2.25 = 24.5

## Key Benefits

### ✅ Automation
- No manual CSV editing
- One command updates all odds
- Applications automatically use latest data

### ✅ Real-Time Data
- Odds from actual sportsbooks
- Multiple markets (DraftKings, FanDuel, etc.)
- Best line selection across bookmakers

### ✅ Historical Tracking
- Each game has unique `event_id`
- Can track line movement over time
- `schedule_date` and `week_label` for temporal analysis

### ✅ Rich Data
- Moneylines (American + Decimal)
- Spreads (both sides)
- Totals (over/under)
- Price factor (vig adjustment)

## Advanced Usage

### Fetch Specific Week
```bash
# Fetch next week's lines
python fetch_odds.py --week-shift 1

# Fetch Week 17
python fetch_odds.py --season 2025 --week 17
```

### Custom Output Path
```bash
python fetch_odds.py --live-file ../data/odds-api/odds_week15.csv
```

### Adjust Vig (Price Factor)
```bash
# More aggressive vig removal
python fetch_odds.py --price-factor 1.025
```

## Validation

### Test Transformation
```bash
cd utils
python test_matchup_migration.py
```

**Expected Output**:
```
✓ Loaded 32 matchup rows
✓ All expected columns present
✓ Spread symmetry verified
✓ ITT calculations correct
✓ matchup_dict and matchup_expanded work correctly
✅ All tests passed!
```

### Verify in Application
1. Run `streamlit run app.py`
2. Navigate to Top Stacks module
3. Check that teams have correct opponents and spreads
4. Verify ITT values match expectations

## Troubleshooting

### Issue: "No odds.csv found"
**Solution**: Run `python fetch_odds.py` to create the file

### Issue: "API key not found"
**Solution**: Set environment variable `ODDS_API_KEY` with your API key from https://the-odds-api.com

### Issue: "Empty odds returned"
**Possible Causes**:
- Outside NFL season (check dates)
- Week already played (games locked)
- API outage (check status)

**Solution**: 
- Verify current NFL week
- Check The Odds API status
- Use fallback: Create `Matchup.csv` manually

### Issue: Transformation error
**Solution**: Check odds.csv format matches expected schema

## Fallback Mode

If `odds.csv` doesn't exist, system automatically falls back to legacy `Matchup.csv`:
```
data/odds-api/odds.csv not found
→ Falls back to: C:\Users\schne\Documents\DFS\2025\Dashboard\Matchup.csv
```

This allows gradual migration and backup options.

## Data Files

### Primary Data Source
- `data/odds-api/odds.csv` - Live odds from API (auto-generated)

### Legacy Files (Optional Backup)
- `C:\Users\schne\Documents\DFS\2025\Dashboard\Matchup.csv` - Manual CSV

### Transformation Code
- `data/data_loader.py` - Contains `load_matchups()` transformation logic

### Test Scripts
- `utils/test_matchup_migration.py` - Validates transformation correctness

## API Limits

**The Odds API Free Tier**:
- 500 requests per month
- Resets monthly
- Monitor usage: `python fetch_odds.py` shows remaining requests

**Request Cost**:
- 1 request per week fetched
- 3 markets (h2h, spreads, totals) counted as 1 request
- Multiple regions counted as 1 request

**Best Practices**:
- Fetch once per week (Tuesday after lines posted)
- Use `--week-shift` to look ahead without extra requests
- Archive historical odds for reference

## Next Steps

### Recommended Workflow:
1. **Tuesday**: Fetch opening lines (`python fetch_odds.py`)
2. **Friday**: Fetch updated lines before injury reports
3. **Sunday AM**: Final line check before contests lock

### Future Enhancements:
- Line movement tracking (opening vs closing)
- Automated scheduled fetches
- Win probability from moneylines
- Player props integration
- Live in-game odds (if needed)

## Support

### Documentation:
- `MATCHUP_MIGRATION.md` - Detailed migration overview
- `utils/claude.md` - Technical documentation
- `plan.md` - Future enhancements roadmap

### Key Functions:
- `fetch_odds.py` - Odds fetching from API
- `data_loader.py:load_matchups()` - Transformation logic
- `test_matchup_migration.py` - Validation tests

---

**Status**: ✅ Migration Complete - All systems operational with odds.csv
