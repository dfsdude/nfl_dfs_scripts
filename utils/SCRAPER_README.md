# FantasyPros Advanced Stats Scraper

Automated scraper that pulls advanced stats for all positions (QB, RB, WR, TE) across all weeks from FantasyPros.

## Features

- ✅ Uses your existing FantasyPros login (no credentials needed)
- ✅ Scrapes all weeks automatically
- ✅ Handles all positions (QB, RB, WR, TE)
- ✅ Outputs clean CSV files
- ✅ Non-destructive (doesn't close your Chrome session)

## Requirements

```bash
pip install selenium beautifulsoup4 pandas
```

## Quick Start

### Step 1: Launch Chrome with Remote Debugging

**Option A - Use the batch script:**
```batch
cd utils
launch_chrome_debug.bat
```

**Option B - Manual command:**
```batch
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/selenium/ChromeProfile"
```

### Step 2: Log into FantasyPros

In the Chrome window that opens, navigate to FantasyPros and log in with your account.

### Step 3: Run the Scraper

```bash
# Scrape all positions, all weeks
python utils/scrape_fantasypros.py -o data/fantasypros/

# Scrape specific positions only
python utils/scrape_fantasypros.py -o data/fantasypros/ --positions QB RB

# Use custom debug port
python utils/scrape_fantasypros.py -o data/fantasypros/ --debug-port 9223
```

## Output

The script creates one CSV file per position:
- `QB_Advanced_Stats_2025.csv`
- `RB_Advanced_Stats_2025.csv`
- `WR_Advanced_Stats_2025.csv`
- `TE_Advanced_Stats_2025.csv`

Each file contains:
- `Week` column (e.g., "Week 1", "Week 2", etc.)
- All player stats for that position
- Combined data across all weeks

## How It Works

1. **Connects to your logged-in Chrome** - Uses Selenium to connect to Chrome running with remote debugging enabled
2. **Navigates to each position page** - QB, RB, WR, TE advanced stats pages
3. **Iterates through weeks** - Selects each week from the dropdown menu
4. **Parses the table** - Extracts data from the HTML table using BeautifulSoup
5. **Aggregates results** - Combines all weeks into a single CSV per position

## Troubleshooting

### "Could not connect to Chrome"
- Make sure Chrome is running with `--remote-debugging-port=9222`
- Check that no other process is using port 9222
- Try closing all Chrome instances and restarting with the batch script

### "Could not find week selector"
- The page might not have loaded fully - increase `time.sleep()` values in the script
- Make sure you're logged into FantasyPros (some stats require login)

### "No data collected"
- Verify you have an active FantasyPros subscription if required
- Check that the current season has started and data is available
- Try manually navigating to the advanced stats page in Chrome to confirm data exists

## Advanced Options

### Custom Week Range
Edit the script to specify custom weeks:
```python
weeks = [
    {'value': '4', 'text': 'Week 4'},
    {'value': '5', 'text': 'Week 5'},
]
scrape_all_positions(output_dir='data/', weeks=weeks)
```

### Rate Limiting
Adjust delays between requests:
```python
time.sleep(2)  # Increase this value to slow down scraping
```

## Notes

- The script leaves your Chrome window open after completion
- Scraping respects FantasyPros' site structure and doesn't overload servers
- Data is parsed from the rendered HTML (same as what you see on the page)
- Works with your existing login session (Premium/MVP status preserved)
