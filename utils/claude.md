# Utils Directory

## Purpose
Utility functions, configuration, helper methods, and data acquisition scripts.

## Files

### `config.py`
Application configuration and constants (paths, settings)

### `constants.py`
Global constants (position lists, scoring rules)

### `data_manager.py`
Global data management and session state

### `helpers.py`
General-purpose helper functions

### `fetch_odds.py`
**Purpose**: Real-time NFL betting odds acquisition from The Odds API

**Key Features**:
- Fetches live moneylines, spreads, and totals from multiple sportsbooks
- Multi-region aggregation (US markets) with best line selection
- Season/week detection (auto-infer current NFL week from schedule)
- Historical odds archival with deduplication
- Price factor adjustment for vig removal (default: 1.022)
- Fallback logic: attempts week+1 if current week returns empty

**API Integration**:
- **Source**: The Odds API (https://the-odds-api.com)
- **Markets**: h2h (moneyline), spreads, totals (over/under)
- **Regions**: us, us2 (American sportsbooks)
- **Format**: American odds → decimal conversion for best line aggregation
- **Rate Limiting**: Tracks API request usage via response headers

**Data Processing**:
1. **Team Normalization**: Maps full names → abbreviations (32 NFL teams)
   - "Kansas City Chiefs" → "KC"
   - "Los Angeles Rams" → "LA"
2. **Odds Conversion**:
   - American → Decimal: `1 + (100/|odds|)` for negative, `1 + (odds/100)` for positive
   - Decimal → American: Reverse calculation for output standardization
3. **Best Line Selection**: Max decimal odds across all bookmakers per team
4. **Season/Week Inference**:
   - Calculates NFL season from UTC timestamp (March cutoff)
   - Week 1 anchor: First Thursday after Labor Day
   - Weeks 1-18: Regular season
   - Weeks 19-22: Playoffs (Wild Card, Divisional, Conference, Super Bowl)

**Output Schema** (`data/live/odds.csv`):
```csv
season, week, week_label, schedule_date, home_team, away_team,
ml_home, ml_away, decimal_home, decimal_away,
ml_home_raw, ml_away_raw, decimal_home_raw, decimal_away_raw,
spread_home, spread_away, over_under_line, price_factor, event_id
```

**CLI Arguments**:
- `--live-file`: Output path (default: `data/live/odds.csv`)
- `--sport`: API sport key (default: `americanfootball_nfl`)
- `--regions`: Sportsbook regions (default: `us,us2`)
- `--markets`: Bet types (default: `h2h,spreads,totals`)
- `--only-current-week`: Fetch only current week (default: True)
- `--season`, `--week`: Override auto-detection for specific week
- `--week-shift`: Offset from current week (e.g., `1` = next week)
- `--price-factor`: Vig adjustment multiplier (default: 1.022)
- `--archive-force`: Force archival update

**Usage Examples**:
```bash
# Fetch current week (auto-detect)
python utils/fetch_odds.py

# Fetch specific week with vig adjustment
python utils/fetch_odds.py --season 2025 --week 15 --price-factor 1.025

# Fetch next week's lines
python utils/fetch_odds.py --week-shift 1

# Custom output path
python utils/fetch_odds.py --live-file data/custom/odds_week15.csv
```

**Key Functions**:
- `fetch_events()`: API request with time window filtering
- `parse_rows()`: Extract odds from nested JSON structure
- `best_decimal()`: Select max decimal odds (best price) across bookmakers
- `infer_week_fields()`: Auto-calculate NFL week from UTC timestamp
- `apply_price_factor()`: Remove vig by dividing decimal odds by factor
- `week_window_utc()`: Calculate Thu-Thu window for specific week

**Integration with DFS Tools**:
- Populates `Matchup.csv` with fresh spreads and totals
- Feeds game script projections (spread → blowout probability)
- Updates implied team totals (ITT) for stack analysis
- Enables live odds tracking throughout the week

**Error Handling**:
- Empty response → attempts fallback week (week+1)
- Missing API key → exits with error
- Offseason detection → skips fetch, returns empty
- Malformed data → returns empty DataFrame, logs warning

**Dependencies**:
- `requests` - HTTP client for API calls
- `pandas` - Data manipulation and CSV I/O
- `numpy` - Numeric operations and NaN handling

**Environment Variables**:
- `ODDS_API_KEY` - Required API authentication key
- `ODDS_PRICE_FACTOR` - Optional vig adjustment (default: 1.022)

### `__init__.py`
Package initialization

## Responsibilities
- Configuration management
- Data directory paths
- Session state management
- Common utility functions (name mapping, data validation)
- Real-time odds acquisition and processing

## Usage
Imported throughout the application for configuration values and helper functions. `fetch_odds.py` runs standalone for data updates.
