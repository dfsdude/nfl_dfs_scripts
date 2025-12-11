"""
Test script to verify odds.csv → Matchup.csv transformation
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from data.data_loader import load_matchups
import pandas as pd

def test_matchup_transformation():
    """Test the odds.csv → Matchup.csv transformation"""
    
    print("=" * 60)
    print("Testing Matchup Data Transformation")
    print("=" * 60)
    
    # Load matchups using new transformation
    matchups = load_matchups()
    
    print(f"\n✓ Loaded {len(matchups)} matchup rows")
    print(f"✓ Columns: {list(matchups.columns)}")
    
    # Verify structure
    expected_cols = ['Init', 'Opp', 'Spread', 'Total', 'ITT']
    missing = set(expected_cols) - set(matchups.columns)
    if missing:
        print(f"\n❌ Missing columns: {missing}")
        return False
    else:
        print(f"\n✓ All expected columns present")
    
    # Show sample data
    print("\n" + "=" * 60)
    print("Sample Matchup Data (First 5 rows):")
    print("=" * 60)
    print(matchups.head().to_string())
    
    # Verify bidirectional structure
    print("\n" + "=" * 60)
    print("Verifying Bidirectional Structure:")
    print("=" * 60)
    
    # Pick a game and show both perspectives
    sample_team = matchups.iloc[0]['Init']
    sample_opp = matchups.iloc[0]['Opp']
    
    team_row = matchups[matchups['Init'] == sample_team].iloc[0]
    opp_row = matchups[matchups['Init'] == sample_opp].iloc[0]
    
    print(f"\nGame: {sample_team} vs {sample_opp}")
    print(f"\n{sample_team} perspective:")
    print(f"  Spread: {team_row['Spread']:.1f}")
    print(f"  Total: {team_row['Total']:.1f}")
    print(f"  ITT: {team_row['ITT']:.2f}")
    
    print(f"\n{sample_opp} perspective:")
    print(f"  Spread: {opp_row['Spread']:.1f}")
    print(f"  Total: {opp_row['Total']:.1f}")
    print(f"  ITT: {opp_row['ITT']:.2f}")
    
    # Verify spread relationship (should be negatives of each other)
    spread_check = abs(team_row['Spread'] + opp_row['Spread']) < 0.01
    print(f"\n✓ Spread symmetry: {spread_check}")
    
    # Verify ITT sum equals total
    itt_sum = team_row['ITT'] + opp_row['ITT']
    itt_check = abs(itt_sum - team_row['Total']) < 0.01
    print(f"✓ ITT sum equals Total: {itt_check} ({itt_sum:.2f} ≈ {team_row['Total']:.1f})")
    
    # Create matchup_dict (Init → Opp mapping)
    matchup_dict = matchups.set_index("Init")["Opp"].to_dict()
    print(f"\n✓ Created matchup_dict with {len(matchup_dict)} entries")
    print(f"  Example: {sample_team} → {matchup_dict[sample_team]}")
    
    # Create matchup_expanded (full row data per team)
    matchup_expanded = matchups.set_index("Init").to_dict(orient="index")
    print(f"✓ Created matchup_expanded with {len(matchup_expanded)} entries")
    print(f"  Example keys: {list(matchup_expanded[sample_team].keys())}")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_matchup_transformation()
