#!/usr/bin/env python3
"""Test delta scraping by simulating missing week"""
import pandas as pd
from pathlib import Path
from scrape_fantasypros import get_existing_weeks, get_available_weeks

output_path = Path('../data/fantasypros')

print("=== Scenario 1: All weeks exist (current state) ===\n")
for pos in ['QB']:
    existing = get_existing_weeks(output_path, pos)
    print(f"{pos} existing: {sorted(existing)}")
    
    # Simulate what scraper would do
    to_scrape = get_available_weeks(None, max_week=14, existing_weeks=existing)
    print(f"Weeks to scrape: {[w['value'] for w in to_scrape]}")
    print(f"Result: {'No scraping needed' if not to_scrape else f'Would scrape {len(to_scrape)} weeks'}\n")

print("=== Scenario 2: Week 15 becomes available ===\n")
existing = get_existing_weeks(output_path, 'QB')
print(f"QB existing: {sorted(existing)}")

# Simulate week 15 being available
to_scrape = get_available_weeks(None, max_week=15, existing_weeks=existing)
print(f"Weeks to scrape: {[w['value'] for w in to_scrape]}")
print(f"Result: {'No scraping needed' if not to_scrape else f'Would scrape {len(to_scrape)} weeks'}")
print(f"Delta: Week(s) {[w['value'] for w in to_scrape]}\n")

print("=== Scenario 3: Fresh start (no existing data) ===\n")
existing = set()  # No existing data
to_scrape = get_available_weeks(None, max_week=14, existing_weeks=existing)
print(f"Weeks to scrape: {[w['value'] for w in to_scrape]}")
print(f"Result: Would scrape all {len(to_scrape)} weeks\n")
