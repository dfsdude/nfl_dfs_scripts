# FantasyPros Advanced Stats Integration Guide

## Overview
Successfully integrated FantasyPros advanced statistics with DraftKings DFS data. The system automatically loads 8,570+ player-week records, aggregates recent performance, and matches players between FantasyPros and DraftKings formats using fuzzy name matching.

## Files Created

### 1. `data/load_advanced_stats.py` - Core Module
**Purpose**: Load, normalize, and merge FantasyPros advanced stats with DraftKings data

**Key Functions**:
```python
# Load all positions (QB, RB, WR, TE)
from data.load_advanced_stats import load_all_advanced_stats
all_stats = load_all_advanced_stats(weeks=[13, 14])  # Optional week filter

# Aggregate recent weeks
from data.load_advanced_stats import aggregate_recent_weeks
recent = aggregate_recent_weeks(all_stats, weeks=4)  # 4-week average

# Merge with DK salaries
from data.load_advanced_stats import merge_with_dk_salaries
merged = merge_with_dk_salaries(recent, dk_salaries_df, week=15)

# Convenience function (all-in-one)
from data.load_advanced_stats import get_recent_advanced_stats
stats = get_recent_advanced_stats(
    lookback_weeks=4,
    dk_salaries=dk_salaries_df,
    current_week=15
)
```

### 2. `utils/test_advanced_stats_integration.py` - Integration Tests
**Purpose**: Comprehensive testing and usage examples

**Test Coverage**:
- ✅ Basic loading (8,570 records)
- ✅ Recent weeks aggregation (613 players)
- ✅ DK salary merging (75.9% match rate)
- ✅ Advanced queries (filtering, value calculations)

## Matching Performance

### Overall Stats
- **Total Players**: 613 (4-week aggregation)
- **Matched**: 465 (75.9%)
- **Exact Matches**: 464 (99.8% of matches)
- **Fuzzy Matches**: 1 (0.2% of matches)
- **Unmatched**: 148 (24.1%)

### By Position
| Position | Matched | Exact | Fuzzy |
|----------|---------|-------|-------|
| QB       | 58      | 58    | 0     |
| RB       | 120     | 120   | 0     |
| WR       | 179     | 178   | 1     |
| TE       | 108     | 108   | 0     |

### Why Some Players Don't Match
1. **Not on DK slate** - Players on bye or injured
2. **Practice squad** - FantasyPros includes PS players
3. **Name variations** - Rare edge cases not in manual mappings
4. **Different teams** - Recent trades/roster moves

## Name Normalization Features

### Automatic Normalization
- **Suffixes**: Jr., Sr., II, III, IV, V removed
- **Apostrophes**: Curly quotes → straight apostrophes
- **Common variations**: Joshua→Josh, Kenneth→Ken, Gabriel→Gabe

### Manual Mappings
```python
'Kenneth Walker': 'Kenneth Walker III'
'A.J. Brown': 'AJ Brown'
'DK Metcalf': 'D.K. Metcalf'
'CJ Stroud': 'C.J. Stroud'
# + more in load_advanced_stats.py
```

### Team Mappings
```python
'JAC': 'JAX'  # Jacksonville
'LAR': 'LA'   # LA Rams
```

### Fuzzy Matching
- **Algorithm**: SequenceMatcher (Levenshtein-like)
- **Threshold**: 85% similarity
- **Team filtering**: Only matches same-team players
- **Fallback**: Exact match first, fuzzy if no exact

## Data Available

### QB Advanced Stats (25 metrics)
Key metrics:
- **AIR/A** - Air Yards per Attempt (deep ball usage)
- **PKT TIME** - Pocket Time (pressure indicator)
- **SACK+KNCK+HRRY** - Total pressure events
- **POOR** - Poor throws (accuracy)
- **DROP** - Receiver drops (WR quality)
- **20+/30+/40+ YDS** - Deep ball frequency

### RB Advanced Stats (25 metrics)
Key metrics:
- **YBCON/YACON** - Yards Before/After Contact
- **BRKTKL** - Broken Tackles (elusiveness)
- **TK LOSS** - Tackles for Loss (OL quality)
- **RZ TGT** - Red Zone Targets (receiving threat)
- **REC/TGT** - Reception rate

### WR/TE Advanced Stats (26 metrics)
Key metrics:
- **YBC/YAC** - Yards Before/After Catch
- **AIR/R** - Air Yards per Reception (route depth)
- **% TM** - % of Team Targets (usage rate)
- **CATCHABLE** - Catchable targets (QB accuracy)
- **DROP** - Dropped passes
- **YACON/R** - Yards After Contact per Reception
- **BRKTKL** - Broken Tackles (RAC ability)
- **RZ TGT** - Red Zone Targets (TD upside)

## Usage Examples

### Example 1: Top Value QBs
```python
from data.load_advanced_stats import get_recent_advanced_stats

# Load 4-week stats merged with DK salaries
stats = get_recent_advanced_stats(lookback_weeks=4, dk_salaries=salaries_df)

# Filter to QBs
qbs = stats[stats['position'] == 'QB'].copy()

# Calculate value (yards per $1K)
qbs['value'] = qbs['YDS_avg_4wk'] / (qbs['Salary'] / 1000)

# Get top 5
top_value = qbs.nlargest(5, 'value')
print(top_value[['Name', 'Salary', 'YDS_avg_4wk', 'value']])
```

**Output**:
```
           Name  Salary  YDS_avg_4wk     value
Jacoby Brissett    5500       335.25 60.954545
     Jared Goff    6100       274.75 45.040984
     Geno Smith    4500       201.00 44.666667
```

### Example 2: Receiving RBs
```python
# Filter to RBs
rbs = stats[stats['position'] == 'RB'].copy()

# Sort by targets
top_receiving = rbs.nlargest(5, 'TGT_avg_4wk')
print(top_receiving[['Name', 'TGT_avg_4wk', 'REC_avg_4wk', 'Salary']])
```

**Output**:
```
          Name  TGT_avg_4wk  REC_avg_4wk  Salary
  Jahmyr Gibbs         7.75         6.50    8800
 Ashton Jeanty         7.00         5.50    5800
   Chase Brown         5.75         4.50    6700
```

### Example 3: High Contact Balance RBs
```python
# Calculate broken tackle rate
rbs['brktkl_per_touch'] = rbs['BRKTKL_avg_4wk'] / (
    rbs['ATT_avg_4wk'] + rbs['REC_avg_4wk']
)

# Filter high rate (>0.15 per touch)
high_contact = rbs[rbs['brktkl_per_touch'] > 0.15]
print(high_contact[['Name', 'brktkl_per_touch', 'Salary']])
```

### Example 4: QBs Under Pressure
```python
# Calculate total pressure events
qbs['pressure_events'] = (
    qbs['SACK_avg_4wk'] + 
    qbs['KNCK_avg_4wk'] + 
    qbs['HRRY_avg_4wk']
)

# Top 5 most pressured
high_pressure = qbs.nlargest(5, 'pressure_events')
print(high_pressure[['Name', 'pressure_events', 'PKT TIME_avg_4wk']])
```

**Output**:
```
           Name  pressure_events  PKT TIME_avg_4wk
Patrick Mahomes            14.50             2.375
Jacoby Brissett            13.00             2.325
       Cam Ward            12.25             2.200
```

### Example 5: WR Target Share Leaders
```python
# Filter to WRs
wrs = stats[stats['position'] == 'WR'].copy()

# Sort by target share
high_share = wrs.nlargest(10, '% TM_avg_4wk')
print(high_share[['Name', '% TM_avg_4wk', 'Salary']])
```

## Integration with Existing Tools

### ROO Simulator
Add advanced stats to volatility calculations:
```python
from data.load_advanced_stats import get_recent_advanced_stats

# Load stats
advanced = get_recent_advanced_stats(lookback_weeks=4, dk_salaries=salaries)

# Merge with player projections
players = players.merge(
    advanced[['Name', 'BRKTKL_avg_4wk', 'YAC_avg_4wk']],
    on='Name',
    how='left'
)

# Adjust volatility based on broken tackles (high contact = high variance)
players.loc[players['position'] == 'RB', 'volatility'] *= (
    1 + (players['BRKTKL_avg_4wk'].fillna(0) * 0.02)
)
```

### Top Stacks Tool
Enhance player filtering:
```python
# Add advanced stats to player pool
players_with_stats = merge_with_dk_salaries(recent_stats, salaries, current_week)

# Filter for high-efficiency RBs
efficient_rbs = players_with_stats[
    (players_with_stats['position'] == 'RB') &
    (players_with_stats['YACON/ATT_avg_4wk'] > 3.0)  # >3 yards after contact
]

# Filter for deep threat WRs
deep_wrs = players_with_stats[
    (players_with_stats['position'] == 'WR') &
    (players_with_stats['AIR/R_avg_4wk'] > 12.0)  # >12 air yards per target
]
```

### Correlation Model
Use advanced stats for role detection:
```python
# Load week-by-week stats
all_stats = load_all_advanced_stats(weeks=list(range(1, 15)))

# Identify alpha WRs (high target share)
alpha_wrs = all_stats[
    (all_stats['position'] == 'WR') &
    (all_stats['% TM'] > 25)  # >25% target share
].groupby('player_normalized')['week_num'].count()

# Identify passing backs (high targets)
passing_backs = all_stats[
    (all_stats['position'] == 'RB') &
    (all_stats['TGT'] >= 4)  # 4+ targets per game
].groupby('player_normalized')['week_num'].count()
```

## Data Updates

### Weekly Refresh
```bash
# 1. Run FantasyPros scraper (delta mode)
cd utils
python scrape_fantasypros.py

# 2. Test integration
python test_advanced_stats_integration.py

# 3. Stats automatically available to all tools
```

### Mid-Week Updates
The scraper only fetches new weeks, so you can run it multiple times:
```bash
# Check for Week 15 data (after games complete)
python scrape_fantasypros.py

# Output: "NO NEW DATA TO SCRAPE" or "Scraped 1 total new weeks"
```

## Performance

### Load Times
- **All positions**: ~1-2 seconds (8,570 records)
- **Aggregation**: <0.5 seconds (613 players)
- **Matching**: ~1 second (613→465 matched)
- **Total**: ~3-4 seconds end-to-end

### Memory Usage
- **Raw data**: ~10 MB (4 CSV files)
- **Loaded DataFrame**: ~15 MB in memory
- **Aggregated**: ~2 MB (613 players)

### Caching
Streamlit cache enabled for data_loader functions:
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_advanced_stats(lookback_weeks=4):
    # Cached after first load
    pass
```

## Troubleshooting

### Issue: Low match rate
**Cause**: DK slate doesn't include all players (byes, injuries)
**Solution**: Normal - 75% is expected for aggregated data

### Issue: Name mismatch
**Cause**: Uncommon name variation not in mappings
**Solution**: Add to `MANUAL_MAPPINGS` in `load_advanced_stats.py`

### Issue: FileNotFoundError
**Cause**: FantasyPros CSVs not scraped yet
**Solution**: Run `python utils/scrape_fantasypros.py`

### Issue: KeyError on column
**Cause**: Column name changed in CSV
**Solution**: Check CSV headers match expected format

## Future Enhancements

### Planned
- [ ] Historical line movement correlation
- [ ] Weather-adjusted efficiency metrics
- [ ] Opponent-adjusted stats (vs top-10 defenses)
- [ ] Trend detection (improving/declining players)

### Possible
- [ ] Real-time injury impact (backup opportunity scoring)
- [ ] Game script adjustment (efficiency in trailing games)
- [ ] Route tree analysis (target depth distribution)
- [ ] Snap count correlation

## Summary

✅ **Complete Integration**
- 8,570 player-week records available
- 75.9% match rate with DK salaries
- Fuzzy matching handles name variations
- 4-week aggregation by default
- Fully tested and documented

✅ **Ready for Use**
- Import and use in any module
- Cached for performance
- Automatic normalization
- Team-based filtering

✅ **Extensible**
- Add custom manual mappings
- Adjust similarity threshold
- Customize aggregation windows
- Extend with new metrics

---

**Status**: ✅ Integration Complete - Production Ready
**Last Updated**: December 10, 2025
