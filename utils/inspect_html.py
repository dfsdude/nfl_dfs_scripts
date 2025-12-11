#!/usr/bin/env python3
"""
Inspect HTML structure to find tables
"""
from bs4 import BeautifulSoup
import sys

html_file = sys.argv[1]

with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# Find all tables
tables = soup.find_all('table')
print(f"Found {len(tables)} table(s)\n")

for i, table in enumerate(tables):
    print(f"Table {i+1}:")
    print(f"  Classes: {table.get('class')}")
    print(f"  ID: {table.get('id')}")
    
    # Count rows
    thead = table.find('thead')
    tbody = table.find('tbody')
    
    header_count = len(thead.find_all('th')) if thead else 0
    row_count = len(tbody.find_all('tr')) if tbody else 0
    
    print(f"  Headers: {header_count}")
    print(f"  Data rows: {row_count}")
    
    if header_count > 0:
        headers = [th.get_text(strip=True) for th in thead.find_all('th')[:5]]
        print(f"  First headers: {headers}")
    
    print()
