"""
Test script for FantasyPros Advanced Stats integration
Demonstrates loading, merging, and using advanced stats with DK salaries
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from data.load_advanced_stats import (
    load_all_advanced_stats,
    aggregate_recent_weeks,
    merge_with_dk_salaries,
    get_recent_advanced_stats,
    normalize_name
)

def test_basic_loading():
    """Test basic data loading"""
    print("=" * 70)
    print("TEST 1: Basic Loading")
    print("=" * 70)
    
    # Load all advanced stats
    all_stats = load_all_advanced_stats()
    
    print(f"\n✓ Loaded {len(all_stats)} player-week records")
    print(f"✓ Weeks: {all_stats['week_num'].min()} to {all_stats['week_num'].max()}")
    print(f"✓ Positions: {', '.join(all_stats['position'].unique())}")
    
    # Show QB sample
    qb_sample = all_stats[all_stats['position'] == 'QB'].head(3)
    print("\nSample QB data:")
    print(qb_sample[['player_normalized', 'team', 'week_num', 'COMP', 'ATT', 'YDS', 'PKT TIME']].to_string(index=False))
    
    # Show RB sample
    rb_sample = all_stats[all_stats['position'] == 'RB'].head(3)
    print("\nSample RB data:")
    print(rb_sample[['player_normalized', 'team', 'week_num', 'ATT', 'YDS', 'BRKTKL', 'REC']].to_string(index=False))
    
    return all_stats


def test_aggregation(all_stats):
    """Test recent weeks aggregation"""
    print("\n" + "=" * 70)
    print("TEST 2: Recent Weeks Aggregation")
    print("=" * 70)
    
    # Aggregate last 4 weeks
    aggregated = aggregate_recent_weeks(all_stats, weeks=4)
    
    print(f"\n✓ Aggregated {len(aggregated)} players (4-week avg)")
    print(f"✓ Games played range: {aggregated['games_played'].min():.0f} to {aggregated['games_played'].max():.0f}")
    
    # Show top QBs by average passing yards
    qb_agg = aggregated[aggregated['position'] == 'QB'].copy()
    if 'YDS_avg_4wk' in qb_agg.columns:
        top_qbs = qb_agg.nlargest(5, 'YDS_avg_4wk')
        print("\nTop 5 QBs by Avg Passing Yards (4 weeks):")
        print(top_qbs[['player_normalized', 'team', 'YDS_avg_4wk', 'games_played']].to_string(index=False))
    
    # Show top RBs by broken tackles
    rb_agg = aggregated[aggregated['position'] == 'RB'].copy()
    if 'BRKTKL_avg_4wk' in rb_agg.columns:
        top_rbs = rb_agg.nlargest(5, 'BRKTKL_avg_4wk')
        print("\nTop 5 RBs by Avg Broken Tackles (4 weeks):")
        print(top_rbs[['player_normalized', 'team', 'BRKTKL_avg_4wk', 'games_played']].to_string(index=False))
    
    return aggregated


def test_dk_merge(aggregated):
    """Test merging with DraftKings salaries"""
    print("\n" + "=" * 70)
    print("TEST 3: DraftKings Salary Merge")
    print("=" * 70)
    
    # Load DK salaries
    dk_salaries_path = Path(r"C:\Users\schne\Documents\DFS\2025\Dashboard\Salaries_2025.csv")
    
    if not dk_salaries_path.exists():
        print("\n⚠ Salaries_2025.csv not found, skipping merge test")
        return None
    
    dk_salaries = pd.read_csv(dk_salaries_path)
    current_week = dk_salaries['Week'].max()
    print(f"\n✓ Loaded DK salaries (Week {current_week})")
    
    # Merge
    merged = merge_with_dk_salaries(aggregated, dk_salaries, current_week)
    
    if len(merged) == 0:
        print("\n❌ No players matched!")
        return None
    
    # Show top value QBs (yards per $1K salary)
    qb_merged = merged[merged['position'] == 'QB'].copy()
    if 'YDS_avg_4wk' in qb_merged.columns and 'Salary' in qb_merged.columns:
        qb_merged['value'] = qb_merged['YDS_avg_4wk'] / (qb_merged['Salary'] / 1000)
        top_value = qb_merged.nlargest(5, 'value')
        print("\nTop 5 Value QBs (Yards per $1K):")
        print(top_value[['Name', 'Salary', 'YDS_avg_4wk', 'value']].to_string(index=False))
    
    # Show top receiving backs (targets)
    rb_merged = merged[merged['position'] == 'RB'].copy()
    if 'TGT_avg_4wk' in rb_merged.columns:
        top_receiving = rb_merged.nlargest(5, 'TGT_avg_4wk')
        print("\nTop 5 Receiving RBs (Avg Targets, 4 weeks):")
        print(top_receiving[['Name', 'team', 'TGT_avg_4wk', 'REC_avg_4wk', 'Salary']].to_string(index=False))
    
    # Show matching stats by position
    print("\n" + "-" * 70)
    print("Matching Statistics by Position:")
    print("-" * 70)
    for pos in ['QB', 'RB', 'WR', 'TE']:
        pos_merged = merged[merged['position'] == pos]
        exact = len(pos_merged[pos_merged['match_type'] == 'exact'])
        fuzzy = len(pos_merged[pos_merged['match_type'] == 'fuzzy'])
        total = len(pos_merged)
        print(f"{pos}: {total} matched ({exact} exact, {fuzzy} fuzzy)")
    
    return merged


def test_advanced_queries(merged):
    """Test advanced filtering and queries"""
    print("\n" + "=" * 70)
    print("TEST 4: Advanced Queries")
    print("=" * 70)
    
    if merged is None or len(merged) == 0:
        print("\n⚠ No merged data available for queries")
        return
    
    # Query 1: RBs with high broken tackle rate
    rb_merged = merged[merged['position'] == 'RB'].copy()
    if 'BRKTKL_avg_4wk' in rb_merged.columns and 'ATT_avg_4wk' in rb_merged.columns:
        rb_merged['brktkl_per_touch'] = rb_merged['BRKTKL_avg_4wk'] / (rb_merged['ATT_avg_4wk'] + rb_merged.get('REC_avg_4wk', 0))
        high_contact = rb_merged[rb_merged['brktkl_per_touch'] > 0.15].nlargest(5, 'brktkl_per_touch')
        
        if len(high_contact) > 0:
            print("\nRBs with High Broken Tackle Rate (>0.15 per touch):")
            print(high_contact[['Name', 'team', 'brktkl_per_touch', 'Salary']].to_string(index=False))
    
    # Query 2: WRs with high target share
    wr_merged = merged[merged['position'] == 'WR'].copy()
    if '% TM_avg_4wk' in wr_merged.columns:
        high_target_share = wr_merged.nlargest(5, '% TM_avg_4wk')
        print("\nWRs with Highest Target Share (4 weeks):")
        print(high_target_share[['Name', 'team', '% TM_avg_4wk', 'Salary']].to_string(index=False))
    
    # Query 3: QBs under pressure
    qb_merged = merged[merged['position'] == 'QB'].copy()
    if all(col in qb_merged.columns for col in ['SACK_avg_4wk', 'KNCK_avg_4wk', 'HRRY_avg_4wk']):
        qb_merged['pressure_events'] = qb_merged['SACK_avg_4wk'] + qb_merged['KNCK_avg_4wk'] + qb_merged['HRRY_avg_4wk']
        high_pressure = qb_merged.nlargest(5, 'pressure_events')
        
        if len(high_pressure) > 0:
            print("\nQBs Facing Most Pressure (Sack+Knock+Hurry, 4 weeks):")
            print(high_pressure[['Name', 'team', 'pressure_events', 'PKT TIME_avg_4wk']].to_string(index=False))


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("FANTASYPROS ADVANCED STATS INTEGRATION TEST")
    print("=" * 70)
    
    try:
        # Test 1: Basic loading
        all_stats = test_basic_loading()
        
        # Test 2: Aggregation
        aggregated = test_aggregation(all_stats)
        
        # Test 3: DK merge
        merged = test_dk_merge(aggregated)
        
        # Test 4: Advanced queries
        test_advanced_queries(merged)
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
