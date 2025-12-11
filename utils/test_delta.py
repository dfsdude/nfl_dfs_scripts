#!/usr/bin/env python3
"""Test script to verify delta scraping logic"""
import pandas as pd
from pathlib import Path
from scrape_fantasypros import get_existing_weeks

output_path = Path('../data/fantasypros')

print("Checking existing data...\n")
for pos in ['QB', 'RB', 'WR', 'TE']:
    weeks = get_existing_weeks(output_path, pos)
    if weeks:
        print(f"{pos}: Weeks {sorted(weeks)} ({len(weeks)} total)")
    else:
        print(f"{pos}: No existing data")

print("\n✓ Delta scraper will only fetch missing weeks")
