#!/usr/bin/env python3
"""
Parse QB Advanced Stats from FantasyPros HTML
Extracts table data and converts to CSV format
"""
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
import re


def parse_qb_stats_html(html_file_path):
    """
    Parse FantasyPros QB stats HTML table and return a DataFrame
    
    Args:
        html_file_path: Path to the HTML file
        
    Returns:
        pandas.DataFrame with QB stats
    """
    # Read the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the main stats table
    # FantasyPros uses id "data" for their stats tables
    table = soup.find('table', {'id': 'data'})
    
    if not table:
        # Fallback: try finding any table with class "table"
        table = soup.find('table', {'class': 'table'})
    
    if not table:
        print("ERROR: Could not find stats table in HTML")
        return None
    
    # Extract headers
    headers = []
    thead = table.find('thead')
    if thead:
        # Get all th elements
        for th in thead.find_all('th'):
            # Extract text, cleaning up any nested elements
            header_text = th.get_text(strip=True)
            # Remove extra whitespace and newlines
            header_text = re.sub(r'\s+', ' ', header_text)
            headers.append(header_text)
    
    print(f"Found {len(headers)} columns: {headers[:5]}...")
    
    # Extract rows
    rows_data = []
    tbody = table.find('tbody')
    if tbody:
        for tr in tbody.find_all('tr'):
            row_data = []
            for td in tr.find_all('td'):
                # Get cell text, handling links and nested elements
                cell_text = td.get_text(strip=True)
                cell_text = re.sub(r'\s+', ' ', cell_text)
                row_data.append(cell_text)
            
            if row_data:  # Only add non-empty rows
                rows_data.append(row_data)
    
    print(f"Found {len(rows_data)} player rows")
    
    # Create DataFrame
    if not rows_data:
        print("WARNING: No data rows found")
        return None
    
    # Ensure all rows have the same number of columns
    expected_cols = len(headers)
    cleaned_rows = []
    for i, row in enumerate(rows_data):
        if len(row) == expected_cols:
            cleaned_rows.append(row)
        else:
            print(f"WARNING: Row {i} has {len(row)} columns, expected {expected_cols}. Skipping.")
    
    if not cleaned_rows:
        print("ERROR: No valid rows after cleaning")
        return None
    
    df = pd.DataFrame(cleaned_rows, columns=headers)
    
    # Clean up player names (remove rank numbers if present)
    if 'Player' in df.columns:
        df['Player'] = df['Player'].str.replace(r'^\d+\.\s*', '', regex=True)
    
    # Convert numeric columns
    numeric_columns = [col for col in df.columns if col not in ['Player', 'Team', 'Opp', 'Pos']]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse FantasyPros QB Advanced Stats HTML')
    parser.add_argument('html_file', type=str, help='Path to HTML file')
    parser.add_argument('-o', '--output', type=str, default=None, 
                       help='Output CSV file (default: same name as input with .csv extension)')
    parser.add_argument('--show-head', action='store_true', 
                       help='Display first 10 rows after parsing')
    
    args = parser.parse_args()
    
    # Parse the HTML
    html_path = Path(args.html_file)
    if not html_path.exists():
        print(f"ERROR: File not found: {html_path}")
        sys.exit(1)
    
    print(f"Parsing {html_path}...")
    df = parse_qb_stats_html(html_path)
    
    if df is None or df.empty:
        print("ERROR: Failed to parse data from HTML")
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = html_path.with_suffix('.csv')
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"\n✓ Saved {len(df)} rows to {output_path}")
    print(f"✓ Columns: {list(df.columns)}")
    
    # Show sample data if requested
    if args.show_head:
        print("\nFirst 10 rows:")
        print(df.head(10).to_string())
    
    # Show basic stats
    print(f"\nData shape: {df.shape[0]} rows x {df.shape[1]} columns")
    if 'Player' in df.columns:
        print(f"Players: {df['Player'].head(5).tolist()}...")


if __name__ == '__main__':
    main()
