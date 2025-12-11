#!/usr/bin/env python3
"""
Scrape FantasyPros Advanced Stats for all positions and weeks
Uses existing Chrome session with active login
"""
import sys
import time
import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import argparse
import sys


# Position URLs for FantasyPros advanced stats
POSITION_URLS = {
    'QB': 'https://www.fantasypros.com/nfl/advanced-stats-qb.php',
    'RB': 'https://www.fantasypros.com/nfl/advanced-stats-rb.php',
    'WR': 'https://www.fantasypros.com/nfl/advanced-stats-wr.php',
    'TE': 'https://www.fantasypros.com/nfl/advanced-stats-te.php',
}


def setup_chrome_driver(debug_port=9222):
    """
    Connect to existing Chrome instance with active login
    
    To use this, start Chrome with remote debugging:
    chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/selenium/ChromeProfile"
    """
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def parse_table_from_html(html_content):
    """Parse the stats table from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the data table
    table = soup.find('table', {'id': 'data'})
    if not table:
        return None
    
    # Extract headers
    headers = []
    thead = table.find('thead')
    if thead:
        for th in thead.find_all('th'):
            header_text = th.get_text(strip=True)
            headers.append(header_text)
    
    # Extract rows
    rows_data = []
    tbody = table.find('tbody')
    if tbody:
        for tr in tbody.find_all('tr'):
            row_data = []
            for td in tr.find_all('td'):
                cell_text = td.get_text(strip=True)
                row_data.append(cell_text)
            
            # Only add rows that have data
            if row_data:
                # If row doesn't match header length, pad or truncate
                if len(row_data) < len(headers):
                    row_data.extend([''] * (len(headers) - len(row_data)))
                elif len(row_data) > len(headers):
                    row_data = row_data[:len(headers)]
                rows_data.append(row_data)
    
    if not rows_data:
        return None
    
    # Create DataFrame
    try:
        df = pd.DataFrame(rows_data, columns=headers)
    except Exception as e:
        print(f"ERROR creating DataFrame: {e}")
        print(f"Headers: {len(headers)}, First row: {len(rows_data[0]) if rows_data else 0}")
        return None
    
    # Clean player names (remove rank numbers)
    if 'Player' in df.columns:
        df['Player'] = df['Player'].str.replace(r'^\d+\.\s*', '', regex=True)
    
    # Convert numeric columns
    numeric_columns = [col for col in df.columns if col not in ['Player', 'Team', 'Opp', 'Pos', 'Week']]
    for col in numeric_columns:
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        except Exception:
            # Silently skip columns that can't be converted
            pass
    
    return df


def get_existing_weeks(output_path, position):
    """
    Get list of weeks already scraped for a position
    
    Args:
        output_path: Path object for output directory
        position: Position code (QB, RB, WR, TE)
    
    Returns:
        Set of week numbers already in the CSV
    """
    csv_file = output_path / f"{position}_Advanced_Stats_2025.csv"
    
    if not csv_file.exists():
        return set()
    
    try:
        df = pd.read_csv(csv_file)
        if 'Week' not in df.columns:
            return set()
        
        # Extract week numbers from "Week X" format
        existing_weeks = set()
        for week_text in df['Week'].unique():
            if isinstance(week_text, str) and week_text.startswith('Week '):
                try:
                    week_num = int(week_text.split()[1])
                    existing_weeks.add(week_num)
                except (ValueError, IndexError):
                    pass
        
        return existing_weeks
    except Exception as e:
        print(f"  Warning: Could not read existing file: {e}")
        return set()


def get_available_weeks(driver, max_week=14, existing_weeks=None):
    """
    Generate list of weeks to scrape (only new weeks not already in CSV)
    
    Args:
        driver: Selenium WebDriver (unused, kept for API compatibility)
        max_week: Maximum week number to scrape
        existing_weeks: Set of weeks already scraped
    
    Returns:
        List of week dicts to scrape (only delta weeks)
    """
    if existing_weeks is None:
        existing_weeks = set()
    
    # Generate all possible weeks
    all_weeks = []
    for week_num in range(1, max_week + 1):
        if week_num not in existing_weeks:
            all_weeks.append({'value': str(week_num), 'text': f'Week {week_num}'})
    
    if not all_weeks:
        return []
    
    if existing_weeks:
        print(f"  Found existing data for weeks: {sorted(existing_weeks)}")
        print(f"  Will scrape new weeks: {sorted([int(w['value']) for w in all_weeks])}")
    else:
        print(f"  No existing data found, will scrape weeks 1-{max_week}")
    
    return all_weeks


def scrape_position_week(driver, position, week_value, week_text):
    """
    Scrape data for a specific position and week
    
    Args:
        driver: Selenium WebDriver
        position: Position code (QB, RB, WR, TE)
        week_value: Week value for dropdown
        week_text: Week text label
        
    Returns:
        DataFrame with stats
    """
    try:
        print(f"  Scraping {position} {week_text}...", end=" ", flush=True)
        
        # Navigate to position page if not already there
        current_url = driver.current_url
        target_url = POSITION_URLS[position]
        if not current_url.startswith(target_url.split('?')[0]):
            driver.get(target_url)
            time.sleep(2)
        
        # Wait for the week input field to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'single-week'))
        )
        
        # Find the week input field and scroll it into view
        week_input = driver.find_element(By.ID, 'single-week')
        driver.execute_script("arguments[0].scrollIntoView(true);", week_input)
        time.sleep(0.5)
        
        # Set the value using JavaScript to avoid interactability issues
        driver.execute_script(f"document.getElementById('single-week').value = '{week_value}';", week_input)
        
        # Click the search button using JavaScript
        search_button = driver.find_element(By.ID, 'range-week-btn')
        driver.execute_script("arguments[0].click();", search_button)
        
        # Wait for table to reload
        time.sleep(3)
        
        # Wait for table to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'data'))
        )
        
        # Get page source and parse table
        html_content = driver.page_source
        df = parse_table_from_html(html_content)
        
        if df is not None and not df.empty:
            # Add week column
            df.insert(0, 'Week', week_text)
            print(f"✓ {len(df)} players")
            return df
        else:
            print("⚠ No data")
            return None
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        # Print more details for debugging
        import traceback
        if '--debug' in sys.argv:
            print(traceback.format_exc())
        return None


def scrape_all_positions(output_dir, positions=None, weeks=None, debug_port=9222):
    """
    Scrape all positions across all weeks
    
    Args:
        output_dir: Directory to save CSV files
        positions: List of positions to scrape (default: all)
        weeks: List of week values to scrape (default: all available)
        debug_port: Chrome remote debugging port
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Connect to Chrome
    print("Connecting to Chrome...")
    driver = setup_chrome_driver(debug_port)
    print(f"✓ Connected to Chrome (current page: {driver.current_url})")
    
    # Determine positions to scrape
    positions_to_scrape = positions if positions else list(POSITION_URLS.keys())
    
    total_new_weeks = 0
    
    try:
        for position in positions_to_scrape:
            print(f"\n{'='*60}")
            print(f"SCRAPING {position}")
            print('='*60)
            
            # Check existing data
            existing_weeks = get_existing_weeks(output_path, position)
            
            # Navigate to position page
            url = POSITION_URLS[position]
            driver.get(url)
            time.sleep(3)
            
            # Get available weeks if not specified (only new weeks)
            if weeks is None:
                available_weeks = get_available_weeks(driver, max_week=14, existing_weeks=existing_weeks)
                if not available_weeks:
                    if existing_weeks:
                        print(f"✓ All weeks already scraped (weeks {sorted(existing_weeks)})")
                    else:
                        print(f"⚠ Could not determine weeks to scrape for {position}, skipping...")
                    continue
            else:
                available_weeks = weeks
            
            total_new_weeks += len(available_weeks)
            print(f"Found {len(available_weeks)} new weeks to scrape")
            
            # Scrape each week
            all_weeks_data = []
            for week_info in available_weeks:
                week_value = week_info['value']
                week_text = week_info['text']
                
                df = scrape_position_week(driver, position, week_value, week_text)
                if df is not None:
                    all_weeks_data.append(df)
                
                # Small delay between weeks
                time.sleep(1)
            
            # Combine all weeks and save/append
            if all_weeks_data:
                new_data_df = pd.concat(all_weeks_data, ignore_index=True)
                output_file = output_path / f"{position}_Advanced_Stats_2025.csv"
                
                # Append to existing file if it exists
                if output_file.exists() and existing_weeks:
                    try:
                        existing_df = pd.read_csv(output_file)
                        combined_df = pd.concat([existing_df, new_data_df], ignore_index=True)
                        combined_df.to_csv(output_file, index=False)
                        print(f"\n✓ Appended {len(new_data_df)} new rows to {output_file} (total: {len(combined_df)} rows)")
                    except Exception as e:
                        print(f"\n⚠ Warning: Could not append to existing file, overwriting: {e}")
                        new_data_df.to_csv(output_file, index=False)
                        print(f"\n✓ Saved {len(new_data_df)} rows to {output_file}")
                else:
                    # No existing file, create new
                    new_data_df.to_csv(output_file, index=False)
                    print(f"\n✓ Saved {len(new_data_df)} rows to {output_file}")
            else:
                print(f"\n⚠ No new data collected for {position}")
    
    finally:
        print("\n" + "="*60)
        if total_new_weeks == 0:
            print("NO NEW DATA TO SCRAPE")
            print("="*60)
            print("\nAll positions are up to date. No scraping needed.")
        else:
            print("SCRAPING COMPLETE")
            print("="*60)
            print(f"\nScraped {total_new_weeks} total new weeks across all positions")
        print("\nNote: Chrome window left open for your use")


def main():
    parser = argparse.ArgumentParser(
        description='Scrape FantasyPros Advanced Stats using logged-in Chrome session',
        epilog="""
SETUP INSTRUCTIONS:
1. Start Chrome with remote debugging (in a separate terminal):
   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/selenium/ChromeProfile"

2. Log into FantasyPros in that Chrome window

3. Run this script:
   python scrape_fantasypros.py --output ../data/fantasypros/

EXAMPLE USAGE:
  # Scrape all positions, all weeks
  python scrape_fantasypros.py -o ../data/fantasypros/
  
  # Scrape only QB and RB
  python scrape_fantasypros.py -o ../data/fantasypros/ --positions QB RB
  
  # Use custom debug port
  python scrape_fantasypros.py -o ../data/fantasypros/ --debug-port 9223
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-o', '--output', type=str, required=True,
                       help='Output directory for CSV files')
    parser.add_argument('--positions', nargs='+', choices=['QB', 'RB', 'WR', 'TE'],
                       help='Positions to scrape (default: all)')
    parser.add_argument('--debug-port', type=int, default=9222,
                       help='Chrome remote debugging port (default: 9222)')
    
    args = parser.parse_args()
    
    # Verify Chrome is running with remote debugging
    print("\n" + "="*60)
    print("FantasyPros Advanced Stats Scraper")
    print("="*60)
    print("\nIMPORTANT: Make sure Chrome is running with remote debugging:")
    print("  chrome.exe --remote-debugging-port=9222 --user-data-dir=\"C:/selenium/ChromeProfile\"")
    print("\nAnd that you are logged into FantasyPros in that Chrome window.")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    try:
        scrape_all_positions(
            output_dir=args.output,
            positions=args.positions,
            debug_port=args.debug_port
        )
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
