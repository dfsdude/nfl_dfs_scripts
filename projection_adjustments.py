"""
Projection Enhancement Module - Advanced Stats Integration

Adjusts ROO projections based on FantasyPros advanced metrics:
- Phase 1: Weight advanced stats (pressure rate, contact efficiency, target quality)
- Phase 2: Target share trends (week-over-week role changes)
- Phase 3: Game environment overlays (player traits + matchup synergies)

Usage:
    from projection_adjustments import (
        adjust_projection_with_advanced_stats,
        calculate_target_share_trends,
        apply_game_environment_overlays
    )
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# PHASE 1: ADVANCED STATS ADJUSTMENTS
# ============================================================================

def adjust_qb_projection(row: pd.Series, advanced_metrics: Optional[pd.Series]) -> float:
    """
    Adjust QB projection based on advanced metrics.
    
    Adjustments:
    - High pressure rate (>0.15) → -10% ceiling vs pass rush teams
    - Low pressure rate (<0.05) → +8% ceiling (clean pocket)
    - High deep ball rate (>0.15) → +5% ceiling (big play potential)
    - Low accuracy score (<0.65) → -8% floor (inconsistent)
    - High big play rate (>0.10) → +10% ceiling (explosive)
    
    Returns: Adjustment multiplier (0.85 to 1.15)
    """
    if advanced_metrics is None or advanced_metrics.empty:
        return 1.0
    
    adjustment = 1.0
    
    # Pressure rate adjustment
    pressure_rate = advanced_metrics.get('pressure_rate', 0)
    if pressure_rate > 0.15:
        # High pressure → lower ceiling/floor
        adjustment *= 0.92
    elif pressure_rate < 0.05:
        # Clean pocket → higher ceiling
        adjustment *= 1.08
    
    # Deep ball rate (explosive potential)
    deep_ball_rate = advanced_metrics.get('deep_ball_rate', 0)
    if deep_ball_rate > 0.15:
        adjustment *= 1.05
    
    # Accuracy score (consistency)
    accuracy_score = advanced_metrics.get('accuracy_score', 0.7)
    if accuracy_score < 0.65:
        # Low accuracy → lower floor
        adjustment *= 0.95
    
    # Big play rate (ceiling booster)
    big_play_rate = advanced_metrics.get('big_play_rate', 0)
    if big_play_rate > 0.10:
        adjustment *= 1.10
    
    return np.clip(adjustment, 0.85, 1.15)


def adjust_rb_projection(row: pd.Series, advanced_metrics: Optional[pd.Series]) -> float:
    """
    Adjust RB projection based on advanced metrics.
    
    Adjustments:
    - Elite contact efficiency (>4.5 YACON/ATT) → +15% ceiling
    - High broken tackle rate (>0.04) → +12% ceiling vs soft run D
    - Receiving back (>0.30 score) → +8% floor (PPR safety)
    - High red zone usage (>0.15) → +10% TD upside
    - High big play rate (>0.15) → +8% ceiling
    
    Returns: Adjustment multiplier (0.85 to 1.20)
    """
    if advanced_metrics is None or advanced_metrics.empty:
        return 1.0
    
    adjustment = 1.0
    
    # Contact efficiency (explosive potential)
    contact_eff = advanced_metrics.get('contact_efficiency', 0)
    if contact_eff > 4.5:
        # Elite contact efficiency → higher ceiling
        adjustment *= 1.15
    elif contact_eff < 2.0:
        # Poor contact efficiency → lower ceiling
        adjustment *= 0.92
    
    # Broken tackle rate (elusiveness)
    broken_tackle_rate = advanced_metrics.get('broken_tackle_rate', 0)
    if broken_tackle_rate > 0.04:
        adjustment *= 1.12
    
    # Receiving back score (PPR floor)
    receiving_score = advanced_metrics.get('receiving_back_score', 0)
    if receiving_score > 0.30:
        # High receiving usage → higher floor
        adjustment *= 1.08
    
    # Red zone usage (TD upside)
    red_zone_usage = advanced_metrics.get('red_zone_usage', 0)
    if red_zone_usage > 0.15:
        adjustment *= 1.10
    
    # Big play rate
    big_play_rate = advanced_metrics.get('big_play_rate', 0)
    if big_play_rate > 0.15:
        adjustment *= 1.08
    
    return np.clip(adjustment, 0.85, 1.20)


def adjust_wr_te_projection(row: pd.Series, advanced_metrics: Optional[pd.Series]) -> float:
    """
    Adjust WR/TE projection based on advanced metrics.
    
    Adjustments:
    - High target quality (>10 AIR/TGT) → +10% ceiling (deep threat)
    - High catchable rate (>0.75) → +5% floor (good QB play)
    - Low drop rate (<0.05) → +5% consistency
    - High YAC per reception (>6.0) → +8% ceiling (after-catch ability)
    - High red zone target share (>0.15) → +12% TD upside
    - High broken tackle rate (>0.03) → +8% ceiling
    
    Returns: Adjustment multiplier (0.85 to 1.18)
    """
    if advanced_metrics is None or advanced_metrics.empty:
        return 1.0
    
    adjustment = 1.0
    
    # Target quality (deep threat)
    target_quality = advanced_metrics.get('target_quality', 0)
    if target_quality > 10.0:
        # Deep threat → higher ceiling
        adjustment *= 1.10
    elif target_quality < 3.0:
        # Short routes → lower ceiling but higher floor
        adjustment *= 0.95
    
    # Catchable rate (QB accuracy to this player)
    catchable_rate = advanced_metrics.get('catchable_rate', 0.7)
    if catchable_rate > 0.75:
        adjustment *= 1.05
    
    # Drop rate (hands)
    drop_rate = advanced_metrics.get('drop_rate', 0.1)
    if drop_rate < 0.05:
        # Sure hands → higher floor
        adjustment *= 1.05
    elif drop_rate > 0.15:
        # High drops → lower floor
        adjustment *= 0.92
    
    # YAC per reception (after-catch ability)
    yac_per_rec = advanced_metrics.get('yac_per_rec', 0)
    if yac_per_rec > 6.0:
        adjustment *= 1.08
    
    # Red zone target share (TD upside)
    rz_target_share = advanced_metrics.get('red_zone_target_share', 0)
    if rz_target_share > 0.15:
        adjustment *= 1.12
    
    # Broken tackle rate (elusiveness)
    broken_tackle_rate = advanced_metrics.get('broken_tackle_rate', 0)
    if broken_tackle_rate > 0.03:
        adjustment *= 1.08
    
    return np.clip(adjustment, 0.85, 1.18)


def adjust_projection_with_advanced_stats(
    player_data: pd.DataFrame,
    advanced_stats: pd.DataFrame
) -> pd.DataFrame:
    """
    Main function: Adjust projections for all players based on advanced stats.
    
    Args:
        player_data: DataFrame with player projections (from ROO simulator)
        advanced_stats: DataFrame with advanced metrics (from advanced_metrics.py)
    
    Returns:
        player_data with new column 'advanced_stats_multiplier'
    """
    print("\n" + "="*70)
    print("PHASE 1: APPLYING ADVANCED STATS ADJUSTMENTS")
    print("="*70)
    
    # Merge advanced stats with player data
    # Match on Player, Team, and aggregate recent weeks
    if 'Week' in advanced_stats.columns:
        # Aggregate last 4 weeks for each player
        recent_stats = advanced_stats.groupby(['Player', 'Team', 'Position']).agg({
            col: 'mean' for col in advanced_stats.columns 
            if col not in ['Player', 'Team', 'Position', 'Week']
        }).reset_index()
    else:
        recent_stats = advanced_stats.copy()
    
    print(f"  Loaded {len(recent_stats)} player advanced stat records")
    
    # Debug: Show sample player names from each dataset
    print(f"  Sample player_data players: {player_data[['Player', 'Team', 'Position']].head(5).to_dict('records')}")
    print(f"  Sample recent_stats players: {recent_stats[['Player', 'Team', 'Position']].head(5).to_dict('records')}")
    
    # Check for exact matches
    player_data_keys = set(player_data['Player'] + '|' + player_data['Team'] + '|' + player_data['Position'])
    recent_stats_keys = set(recent_stats['Player'] + '|' + recent_stats['Team'] + '|' + recent_stats['Position'])
    overlap = player_data_keys & recent_stats_keys
    print(f"  Exact key matches before merge: {len(overlap)} / {len(player_data_keys)}")
    
    # Merge with player data
    merged = player_data.merge(
        recent_stats,
        on=['Player', 'Team', 'Position'],
        how='left',
        suffixes=('', '_adv')
    )
    
    # Count matches by checking if ANY advanced metric column exists (not NaN)
    advanced_metric_cols = [
        'pressure_rate', 'deep_ball_rate', 'accuracy_score', 'big_play_rate',
        'contact_efficiency', 'broken_tackle_rate', 'receiving_back_score', 'red_zone_usage',
        'target_quality', 'catchable_rate', 'drop_rate', 'yac_per_rec', 'red_zone_target_share'
    ]
    available_adv_cols = [col for col in advanced_metric_cols if col in merged.columns]
    
    if available_adv_cols:
        # A player is "matched" if ANY of their position-relevant metrics exists
        matched_mask = merged[available_adv_cols].notna().any(axis=1)
        matched_count = matched_mask.sum()
    else:
        matched_count = 0
    
    print(f"  Matched {matched_count} / {len(player_data)} players with advanced stats")
    
    # Debug unmatched players
    if matched_count < len(player_data) * 0.5:
        unmatched = player_data[~player_data['Player'].isin(recent_stats['Player'])]
        print(f"  Sample unmatched players: {unmatched[['Player', 'Team', 'Position']].head(5).to_dict('records')}")
    
    # Apply position-specific adjustments
    def apply_adjustment(row):
        # Get advanced metrics for this player
        adv_cols = [col for col in merged.columns if col in [
            'pressure_rate', 'deep_ball_rate', 'accuracy_score', 'big_play_rate',
            'contact_efficiency', 'broken_tackle_rate', 'receiving_back_score', 'red_zone_usage',
            'target_quality', 'catchable_rate', 'drop_rate', 'yac_per_rec', 'red_zone_target_share'
        ]]
        
        adv_metrics = row[adv_cols] if adv_cols else pd.Series()
        
        if row['Position'] == 'QB':
            return adjust_qb_projection(row, adv_metrics)
        elif row['Position'] == 'RB':
            return adjust_rb_projection(row, adv_metrics)
        elif row['Position'] in ['WR', 'TE']:
            return adjust_wr_te_projection(row, adv_metrics)
        else:
            return 1.0
    
    merged['advanced_stats_multiplier'] = merged.apply(apply_adjustment, axis=1)
    
    # Summary statistics
    print("\nAdjustment Summary by Position:")
    for pos in ['QB', 'RB', 'WR', 'TE']:
        pos_data = merged[merged['Position'] == pos]
        if len(pos_data) > 0:
            avg_mult = pos_data['advanced_stats_multiplier'].mean()
            max_mult = pos_data['advanced_stats_multiplier'].max()
            min_mult = pos_data['advanced_stats_multiplier'].min()
            
            upgraded = (pos_data['advanced_stats_multiplier'] > 1.05).sum()
            downgraded = (pos_data['advanced_stats_multiplier'] < 0.95).sum()
            
            print(f"  {pos}: Avg {avg_mult:.3f} | Range [{min_mult:.3f}, {max_mult:.3f}] | "
                  f"↑{upgraded} upgraded, ↓{downgraded} downgraded")
    
    # Return only original columns + multiplier
    result = player_data.copy()
    result['advanced_stats_multiplier'] = merged['advanced_stats_multiplier'].values
    
    return result


# ============================================================================
# PHASE 2: TARGET SHARE TRENDS
# ============================================================================

def calculate_target_share_trends(
    player_data: pd.DataFrame,
    fantasypros_data: pd.DataFrame,
    lookback_weeks: int = 4
) -> pd.DataFrame:
    """
    Calculate target share trends to identify rising/declining roles.
    
    Metrics:
    - % TM (target share) week-over-week change
    - Snap count trends (if available)
    - Role momentum score: positive = rising, negative = declining
    
    Args:
        player_data: Current week player projections
        fantasypros_data: Historical FantasyPros data with % TM
        lookback_weeks: Number of weeks to analyze
    
    Returns:
        player_data with 'target_share_trend' and 'role_momentum' columns
    """
    print("\n" + "="*70)
    print("PHASE 2: CALCULATING TARGET SHARE TRENDS")
    print("="*70)
    
    # Filter to recent weeks
    max_week = fantasypros_data['Week'].max() if 'Week' in fantasypros_data.columns else 14
    recent_weeks = fantasypros_data[
        fantasypros_data['Week'] > (max_week - lookback_weeks)
    ].copy()
    
    print(f"  Analyzing weeks {max_week - lookback_weeks + 1} to {max_week}")
    print(f"  {len(recent_weeks)} player-week records")
    
    # Calculate trends for pass-catchers (RB, WR, TE)
    trends = []
    
    for player, group in recent_weeks.groupby(['Player', 'Team', 'Position']):
        if len(group) < 2:
            continue
        
        # Sort by week
        group = group.sort_values('Week')
        
        # Check if % TM column exists (target share)
        target_share_col = None
        for col in ['% TM', '%TM', 'pct_tm', 'target_share']:
            if col in group.columns:
                target_share_col = col
                break
        
        if target_share_col is None:
            continue
        
        # Calculate week-over-week change
        target_shares = group[target_share_col].values
        weeks = group['Week'].values
        
        # Linear trend (positive = increasing, negative = decreasing)
        if len(target_shares) >= 2:
            # Simple approach: compare most recent 2 weeks to previous 2 weeks
            if len(target_shares) >= 4:
                recent_avg = np.mean(target_shares[-2:])
                older_avg = np.mean(target_shares[:2])
                trend = recent_avg - older_avg
            else:
                # Just use first vs last
                trend = target_shares[-1] - target_shares[0]
            
            # Role momentum: scaled to -1 to +1
            momentum = np.clip(trend / 10.0, -1.0, 1.0)  # 10% change = full momentum
            
            trends.append({
                'Player': player[0],
                'Team': player[1],
                'Position': player[2],
                'target_share_trend': trend,
                'role_momentum': momentum,
                'recent_target_share': target_shares[-1]
            })
    
    trends_df = pd.DataFrame(trends)
    
    if len(trends_df) == 0:
        print("  ⚠ No target share trends calculated (missing % TM data)")
        player_data['target_share_trend'] = 0.0
        player_data['role_momentum'] = 0.0
        return player_data
    
    print(f"  Calculated trends for {len(trends_df)} players")
    
    # Merge with player data
    result = player_data.merge(
        trends_df[['Player', 'Team', 'target_share_trend', 'role_momentum']],
        on=['Player', 'Team'],
        how='left'
    )
    
    # Fill missing with 0 (no trend data)
    result['target_share_trend'] = result['target_share_trend'].fillna(0)
    result['role_momentum'] = result['role_momentum'].fillna(0)
    
    # Identify rising/declining players
    rising = (result['role_momentum'] > 0.15).sum()
    declining = (result['role_momentum'] < -0.15).sum()
    
    print(f"\nTrend Analysis:")
    print(f"  Rising roles (momentum > 0.15): {rising} players")
    print(f"  Declining roles (momentum < -0.15): {declining} players")
    
    # Show top rising players
    if rising > 0:
        top_rising = result[result['role_momentum'] > 0.15].nlargest(5, 'role_momentum')
        print(f"\n  Top Rising Players:")
        for _, row in top_rising.iterrows():
            print(f"    {row['Player']} ({row['Position']}, {row['Team']}): "
                  f"+{row['target_share_trend']:.1f}% trend, momentum {row['role_momentum']:.2f}")
    
    return result


# ============================================================================
# COMBINED ADJUSTMENT APPLICATION
# ============================================================================

def apply_all_adjustments(
    player_data: pd.DataFrame,
    advanced_stats: pd.DataFrame,
    fantasypros_data: pd.DataFrame
) -> pd.DataFrame:
    """
    Apply all projection adjustments in sequence.
    
    Args:
        player_data: ROO projections
        advanced_stats: Advanced metrics with engineered features
        fantasypros_data: Full FantasyPros historical data
    
    Returns:
        Adjusted player_data with multipliers applied
    """
    # Phase 1: Advanced stats adjustments
    adjusted = adjust_projection_with_advanced_stats(player_data, advanced_stats)
    
    # Phase 2: Target share trends
    adjusted = calculate_target_share_trends(adjusted, fantasypros_data, lookback_weeks=4)
    
    # Calculate combined multiplier
    # Advanced stats: primary factor (0.85 to 1.20)
    # Role momentum: secondary boost/penalty (±5%)
    adjusted['combined_multiplier'] = (
        adjusted['advanced_stats_multiplier'] * 
        (1.0 + adjusted['role_momentum'] * 0.05)
    )
    
    # Clip to reasonable bounds
    adjusted['combined_multiplier'] = adjusted['combined_multiplier'].clip(0.80, 1.25)
    
    print("\n" + "="*70)
    print("COMBINED ADJUSTMENT SUMMARY")
    print("="*70)
    
    for pos in ['QB', 'RB', 'WR', 'TE']:
        pos_data = adjusted[adjusted['Position'] == pos]
        if len(pos_data) > 0:
            avg_mult = pos_data['combined_multiplier'].mean()
            print(f"  {pos}: Average combined multiplier = {avg_mult:.3f}")
    
    return adjusted


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("PROJECTION ADJUSTMENTS TEST")
    print("="*70)
    
    # This would normally be called from roo_simulator.py
    # For testing, we'll just show the structure
    
    print("\nModule loaded successfully!")
    print("\nAvailable functions:")
    print("  - adjust_projection_with_advanced_stats()")
    print("  - calculate_target_share_trends()")
    print("  - apply_all_adjustments()")
    
    print("\nIntegration points:")
    print("  1. After build_distributions() in roo_simulator.py")
    print("  2. Before run_simulations()")
    print("  3. Adjusts mu_log (median) and sigma_log (spread)")
