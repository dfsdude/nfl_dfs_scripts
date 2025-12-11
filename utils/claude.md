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

**Output Schema** (`../data/odds-api/odds.csv`):
```csv
season, week, week_label, schedule_date, home_team, away_team,
ml_home, ml_away, decimal_home, decimal_away,
ml_home_raw, ml_away_raw, decimal_home_raw, decimal_away_raw,
spread_home, spread_away, over_under_line, price_factor, event_id
```

**CLI Arguments**:
- `--live-file`: Output path (default: `../data/odds-api/odds.csv`)
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
python utils/fetch_odds.py --live-file ../data/odds-api/odds_week15.csv
```

**Key Functions**:
- `fetch_events()`: API request with time window filtering
- `parse_rows()`: Extract odds from nested JSON structure
- `best_decimal()`: Select max decimal odds (best price) across bookmakers
- `infer_week_fields()`: Auto-calculate NFL week from UTC timestamp
- `apply_price_factor()`: Remove vig by dividing decimal odds by factor
- `week_window_utc()`: Calculate Thu-Thu window for specific week

**Integration with DFS Tools**:
- Automatically transforms to `Matchup.csv` format via `data/data_loader.py`
- Populates matchup data with fresh spreads and totals
- Feeds game script projections (spread → blowout probability)
- Updates implied team totals (ITT) for stack analysis
- Enables live odds tracking throughout the week

**Matchup Transformation** (`data/data_loader.py` - `load_matchups()`):
- Reads `odds.csv` (home/away format, 1 row per game)
- Transforms to `Matchup.csv` format (Init/Opp bidirectional, 2 rows per game)
- **Home team row**: Init=home, Opp=away, Spread=spread_home
- **Away team row**: Init=away, Opp=home, Spread=-spread_home
- **ITT Calculation**: (Total/2) + (Spread/2) = Implied Team Total
- **Example**: TB @ ATL, spread -4.5, total 44.5
  - TB row: Spread=-4.5, ITT=20.0
  - ATL row: Spread=+4.5, ITT=24.5
- Used by: `roo_simulator.py`, `modules/top_stacks.py`
- Creates: `matchup_dict` (Init→Opp), `matchup_expanded` (full row data)

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

---

### `scrape_fantasypros.py`
**Purpose**: Automated web scraper for FantasyPros Advanced Stats using Selenium with Chrome remote debugging

**Key Features**:
- Connects to logged-in Chrome session (bypasses authentication)
- **Delta scraping**: Only fetches new weeks not already in CSV files
- Gracefully exits if no new data available
- Appends new weeks to existing CSVs (preserves historical data)
- Iterates through all positions (QB, RB, WR, TE) and weeks (1-14+)
- Uses JavaScript execution to interact with hidden/covered UI elements
- Robust table parsing with BeautifulSoup
- Automatic row/column alignment and numeric conversion
- Position-specific CSV output with week labels

**Architecture**:
- **Chrome Remote Debugging**: Attaches to existing Chrome instance on port 9222
- **Week Navigation**: Inputs week number → clicks search button → waits for table reload
- **HTML Parsing**: Extracts table#data, handles mismatched column counts
- **Error Handling**: Skips failed weeks, continues scraping, reports summary

**Data Output** (`../data/fantasypros/*.csv`):
- `QB_Advanced_Stats_2025.csv` - 1,082 rows (77-78 QBs × 14 weeks)
- `RB_Advanced_Stats_2025.csv` - 2,201 rows (156-159 RBs × 14 weeks)
- `WR_Advanced_Stats_2025.csv` - 3,302 rows (235-237 WRs × 14 weeks)
- `TE_Advanced_Stats_2025.csv` - 1,985 rows (141-143 TEs × 14 weeks)

**QB Advanced Stats** (25 columns):
```
Week, Rank, Player, G, COMP, ATT, PCT, YDS, Y/A, AIR, AIR/A,
10+ YDS, 20+ YDS, 30+ YDS, 40+ YDS, 50+ YDS, PKT TIME,
SACK, KNCK, HRRY, BLITZ, POOR, DROP, RZ ATT, RTG
```

**Key QB Metrics**:
- `AIR/A` (Air Yards/Attempt) - Average depth of target, indicates aggressiveness
- `PKT TIME` (Pocket Time) - Avg seconds before throw/sack (pressure indicator)
- `SACK+KNCK+HRRY` - Total pressure events (combine for pressure rate)
- `POOR` - Poor throws (accuracy metric, inaccurate passes)
- `DROP` - Receiver drops (WR quality indicator)
- `BLITZ` - Times blitzed (defense aggression faced)
- `20+/30+/40+ YDS` - Deep ball frequency (explosiveness)

**RB Advanced Stats** (25 columns):
```
Week, Rank, Player, G, ATT, YDS, Y/ATT, YBCON, YBCON/ATT,
YACON, YACON/ATT, BRKTKL, TK LOSS, TK LOSS YDS, LNG TD,
10+ YDS, 20+ YDS, 30+ YDS, 40+ YDS, 50+ YDS, LNG,
REC, TGT, RZ TGT, YACON (duplicate)
```

**Key RB Metrics**:
- `YBCON/YACON` - Yards Before/After Contact (efficiency, vision, power)
- `BRKTKL` (Broken Tackles) - Elusiveness, contact balance
- `TK LOSS` - Tackles for loss (OL quality, bad run defense indicator)
- `RZ TGT` (Red Zone Targets) - Receiving threat inside 20-yard line
- `REC/TGT` - Reception rate (hands, route running)
- `10+/20+ YDS` - Explosiveness (big play capability)

**WR/TE Advanced Stats** (26 columns):
```
Week, Rank, Player, G, REC, YDS, Y/R, YBC, YBC/R,
AIR, AIR/R, YAC, YAC/R, YACON, YACON/R, BRKTKL, TGT, % TM,
CATCHABLE, DROP, RZ TGT, 10+ YDS, 20+ YDS, 30+ YDS, 40+ YDS, 50+ YDS, LNG
```

**Key WR/TE Metrics**:
- `YBC/YAC` - Yards Before/After Catch (separation vs RAC ability)
- `AIR/R` (Air Yards per Reception) - Route depth, downfield threat
- `% TM` (% of Team Targets) - Target share, usage rate
- `CATCHABLE` - Catchable targets (QB accuracy to this player)
- `DROP` - Dropped passes (hands, concentration)
- `YACON/R` (Yards After Contact per Reception) - YAC + contact balance
- `BRKTKL` - Broken tackles (elusiveness after catch)
- `RZ TGT` - Red zone targets (TD upside)

**Setup Requirements**:
1. **Chrome Launch**: `launch_chrome_debug.bat` starts Chrome on port 9222
   - Auto-detects Chrome path (3 common locations)
   - Uses separate profile to preserve login state
2. **Manual Login**: User logs into FantasyPros in debug Chrome
3. **Scraper Execution**: Connects to existing session, no authentication needed

**CLI Arguments**:
- `-o, --output`: Output directory (default: `data/fantasypros/`)
- `--positions`: Specific positions to scrape (default: all 4)
- `--debug-port`: Chrome remote debugging port (default: 9222)

**Usage Examples**:
```bash
# Launch Chrome with remote debugging
.\launch_chrome_debug.bat

# Scrape all positions for all weeks
python scrape_fantasypros.py -o ../data/fantasypros/

# Scrape only QB and RB
python scrape_fantasypros.py -o ../data/ --positions QB RB

# Use custom debug port
python scrape_fantasypros.py -o ../data/ --debug-port 9223
```

**Key Functions**:
- `get_existing_weeks(output_path, position)` - Scans CSV for existing week data
  - Returns set of week numbers already scraped
  - Handles missing files gracefully
- `get_available_weeks(driver, max_week, existing_weeks)` - Generates delta week list
  - Only returns weeks NOT in existing_weeks set
  - Prints helpful messages about existing vs new weeks
- `setup_chrome_driver(debug_port)` - Connects to existing Chrome session
- `scrape_position_week(driver, position, week_value, week_text)` - Single scrape
  - Scrolls week input into view
  - Sets value via JavaScript (avoids "element not interactable" errors)
  - Clicks search button via JavaScript
  - Waits 3 seconds for table reload
  - Parses HTML with BeautifulSoup
- `parse_table_from_html(html_content)` - Extract table#data
  - Handles mismatched row/column counts (padding/truncation)
  - Cleans player names (removes rank prefix)
  - Converts numeric columns (silently skips problematic ones like YACON)
- `scrape_all_positions(output_dir, positions, weeks, debug_port)` - Orchestrator
  - Checks existing data before scraping each position
  - Iterates positions → delta weeks only
  - Appends new weeks to existing CSVs
  - Reports total new weeks scraped
  - Gracefully exits if all data current

**Error Handling**:
- Element not found → logs error, skips week, continues
- Table parsing failure → returns None, skips week
- Chrome connection failure → exits with message
- Missing table → returns None, logs "No data"

**Performance**:
- 3-second wait per week (table reload)
- 1-second delay between weeks
- **Delta mode**: Only scrapes missing weeks (much faster on subsequent runs)
  - First run: ~4-5 minutes (56 total scrapes: 4 positions × 14 weeks)
  - Subsequent runs: Seconds (if all data current) to ~1-2 minutes (1-2 new weeks)
- Graceful exit: Exits immediately if no new weeks found

**Integration Roadmap** (see plan.md):
1. **Data Loading**: Create `load_advanced_stats.py` for CSV ingestion
2. **Player Matching**: Fuzzy name matching between FantasyPros and DK formats
3. **Feature Engineering**: Derive metrics (pressure rate, efficiency scores)
4. **UI Integration**: Add "Advanced Stats" tabs, enhanced filters
5. **Projection Enhancement**: Weight advanced stats into ROO projections

**Dependencies**:
- `selenium` - WebDriver automation
- `beautifulsoup4` - HTML parsing
- `pandas` - Data manipulation and CSV I/O
- `argparse` - CLI argument parsing

---

### `parse_qb_stats.py`
**Purpose**: HTML table parser for saved FantasyPros pages (development/testing)

**Usage**: One-off parsing of local HTML files before full scraper implementation
- Input: Saved HTML file (e.g., `QB_Stats.html`)
- Output: Cleaned CSV with extracted table data
- Successfully parsed 78 QBs with 24 columns from test file

**Status**: Superseded by `scrape_fantasypros.py` for production use

---

### `launch_chrome_debug.bat`
**Purpose**: Windows batch script to launch Chrome with remote debugging enabled

**Features**:
- Auto-detects Chrome installation in 3 common paths:
  1. `C:\Program Files\Google\Chrome\Application\chrome.exe`
  2. `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
  3. `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`
- Uses separate user profile (`C:/selenium/ChromeProfile`)
- Enables remote debugging on port 9222
- Preserves login state across scraper runs

**Usage**:
```cmd
launch_chrome_debug.bat
```

**Note**: Leave this Chrome window open during scraping - scraper attaches to it

---

### `SCRAPER_README.md`
**Purpose**: Standalone documentation for FantasyPros scraper setup and usage

**Contents**: Installation steps, Chrome setup, troubleshooting, data schema

---

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
