"""
Advanced Stats Feature Engineering Module

Derives advanced metrics from FantasyPros raw stats:
- QB: Pressure rate, Deep ball rate, Efficiency metrics
- RB: Contact efficiency, Broken tackle rate, Usage metrics
- WR/TE: Target quality, Separation metrics, Route efficiency

Usage:
    from advanced_metrics import (
        calculate_qb_advanced_metrics,
        calculate_rb_advanced_metrics,
        calculate_wr_te_advanced_metrics,
        add_all_advanced_metrics
    )
    
    # Add metrics to FantasyPros data
    fp_data = load_fantasypros_data()
    enriched_data = add_all_advanced_metrics(fp_data)
"""

import pandas as pd
import numpy as np
from typing import Optional


def calculate_qb_advanced_metrics(qb_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate advanced QB metrics from FantasyPros data.
    
    Metrics:
    - Pressure Rate: (SACK + KNCK + HRRY) / (ATT + SACK)
    - Deep Ball Rate: 20+ YDS completions / ATT
    - Aggressive Rate: 30+ YDS completions / ATT
    - Poor Throw Rate: POOR / ATT
    - Drop Impact: DROP / ATT (receiver quality indicator)
    - Time to Throw: PKT TIME (already provided)
    - Accuracy Score: (ATT - POOR - DROP) / ATT
    - Big Play Rate: (30+ YDS + 40+ YDS + 50+ YDS) / ATT
    
    Args:
        qb_df: DataFrame with QB stats from FantasyPros
    
    Returns:
        DataFrame with added advanced metric columns
    """
    df = qb_df.copy()
    
    # Pressure Rate: Total pressure events per dropback
    if all(col in df.columns for col in ['SACK', 'KNCK', 'HRRY', 'ATT']):
        df['total_pressure'] = df['SACK'].fillna(0) + df['KNCK'].fillna(0) + df['HRRY'].fillna(0)
        df['dropbacks'] = df['ATT'].fillna(0) + df['SACK'].fillna(0)
        df['pressure_rate'] = np.where(
            df['dropbacks'] > 0,
            df['total_pressure'] / df['dropbacks'],
            0
        )
        df['pressure_rate'] = df['pressure_rate'].round(3)
    
    # Deep Ball Rate: 20+ yard completions per attempt
    if all(col in df.columns for col in ['20+ YDS', 'ATT']):
        df['deep_ball_rate'] = np.where(
            df['ATT'] > 0,
            df['20+ YDS'].fillna(0) / df['ATT'],
            0
        )
        df['deep_ball_rate'] = df['deep_ball_rate'].round(3)
    
    # Aggressive Rate: 30+ yard completions per attempt
    if all(col in df.columns for col in ['30+ YDS', 'ATT']):
        df['aggressive_rate'] = np.where(
            df['ATT'] > 0,
            df['30+ YDS'].fillna(0) / df['ATT'],
            0
        )
        df['aggressive_rate'] = df['aggressive_rate'].round(3)
    
    # Poor Throw Rate
    if all(col in df.columns for col in ['POOR', 'ATT']):
        df['poor_throw_rate'] = np.where(
            df['ATT'] > 0,
            df['POOR'].fillna(0) / df['ATT'],
            0
        )
        df['poor_throw_rate'] = df['poor_throw_rate'].round(3)
    
    # Drop Impact (higher = WRs dropping more)
    if all(col in df.columns for col in ['DROP', 'ATT']):
        df['drop_impact'] = np.where(
            df['ATT'] > 0,
            df['DROP'].fillna(0) / df['ATT'],
            0
        )
        df['drop_impact'] = df['drop_impact'].round(3)
    
    # Accuracy Score (clean throws / attempts)
    if all(col in df.columns for col in ['ATT', 'POOR', 'DROP']):
        df['clean_throws'] = df['ATT'].fillna(0) - df['POOR'].fillna(0) - df['DROP'].fillna(0)
        df['accuracy_score'] = np.where(
            df['ATT'] > 0,
            df['clean_throws'] / df['ATT'],
            0
        )
        df['accuracy_score'] = df['accuracy_score'].clip(0, 1).round(3)
    
    # Big Play Rate: Sum of all explosive plays
    big_play_cols = ['30+ YDS', '40+ YDS', '50+ YDS']
    if all(col in df.columns for col in big_play_cols + ['ATT']):
        df['big_plays'] = df[big_play_cols].fillna(0).sum(axis=1)
        df['big_play_rate'] = np.where(
            df['ATT'] > 0,
            df['big_plays'] / df['ATT'],
            0
        )
        df['big_play_rate'] = df['big_play_rate'].round(3)
    
    # Air Yards per Attempt (already provided as AIR/A)
    # PKT TIME already provided
    
    return df


def calculate_rb_advanced_metrics(rb_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate advanced RB metrics from FantasyPros data.
    
    Metrics:
    - Contact Efficiency: YACON/ATT (yards after contact per carry)
    - Before Contact Efficiency: YBCON/ATT
    - Broken Tackle Rate: BRKTKL / touches
    - Tackle Loss Rate: TK LOSS / ATT
    - Receiving Back Score: REC / (ATT + REC) - receiving usage
    - Red Zone Usage: RZ TGT / total opportunities
    - Big Play Rate: (20+ YDS + 30+ YDS + 40+ YDS) / ATT
    - Touch Efficiency: (YDS + REC*10) / touches
    
    Args:
        rb_df: DataFrame with RB stats from FantasyPros
    
    Returns:
        DataFrame with added advanced metric columns
    """
    df = rb_df.copy()
    
    # Calculate total touches
    if all(col in df.columns for col in ['ATT', 'REC']):
        df['touches'] = df['ATT'].fillna(0) + df['REC'].fillna(0)
    
    # Contact Efficiency: YACON/ATT (already calculated as YACON/ATT in data)
    # Keep the original if it exists, otherwise calculate
    if 'YACON/ATT' not in df.columns and all(col in df.columns for col in ['YACON', 'ATT']):
        df['contact_efficiency'] = np.where(
            df['ATT'] > 0,
            df['YACON'].fillna(0) / df['ATT'],
            0
        )
        df['contact_efficiency'] = df['contact_efficiency'].round(2)
    else:
        df['contact_efficiency'] = df['YACON/ATT'].fillna(0).round(2)
    
    # Before Contact Efficiency
    if 'YBCON/ATT' not in df.columns and all(col in df.columns for col in ['YBCON', 'ATT']):
        df['before_contact_efficiency'] = np.where(
            df['ATT'] > 0,
            df['YBCON'].fillna(0) / df['ATT'],
            0
        )
        df['before_contact_efficiency'] = df['before_contact_efficiency'].round(2)
    else:
        df['before_contact_efficiency'] = df['YBCON/ATT'].fillna(0).round(2)
    
    # Broken Tackle Rate per touch
    if all(col in df.columns for col in ['BRKTKL', 'touches']):
        df['broken_tackle_rate'] = np.where(
            df['touches'] > 0,
            df['BRKTKL'].fillna(0) / df['touches'],
            0
        )
        df['broken_tackle_rate'] = df['broken_tackle_rate'].round(3)
    
    # Tackle Loss Rate (negative plays)
    if all(col in df.columns for col in ['TK LOSS', 'ATT']):
        df['tackle_loss_rate'] = np.where(
            df['ATT'] > 0,
            df['TK LOSS'].fillna(0) / df['ATT'],
            0
        )
        df['tackle_loss_rate'] = df['tackle_loss_rate'].round(3)
    
    # Receiving Back Score (0 = pure rusher, 1 = pure receiver)
    if 'touches' in df.columns:
        df['receiving_back_score'] = np.where(
            df['touches'] > 0,
            df['REC'].fillna(0) / df['touches'],
            0
        )
        df['receiving_back_score'] = df['receiving_back_score'].round(3)
    
    # Red Zone Usage
    if all(col in df.columns for col in ['RZ TGT', 'touches']):
        df['red_zone_usage'] = np.where(
            df['touches'] > 0,
            df['RZ TGT'].fillna(0) / df['touches'],
            0
        )
        df['red_zone_usage'] = df['red_zone_usage'].round(3)
    
    # Big Play Rate
    big_play_cols = ['20+ YDS', '30+ YDS', '40+ YDS']
    existing_cols = [col for col in big_play_cols if col in df.columns]
    if existing_cols and 'ATT' in df.columns:
        df['big_plays'] = df[existing_cols].fillna(0).sum(axis=1)
        df['big_play_rate'] = np.where(
            df['ATT'] > 0,
            df['big_plays'] / df['ATT'],
            0
        )
        df['big_play_rate'] = df['big_play_rate'].round(3)
    
    # Touch Efficiency (fantasy points per touch, simplified)
    if all(col in df.columns for col in ['YDS', 'REC', 'touches']):
        df['fantasy_per_touch'] = np.where(
            df['touches'] > 0,
            (df['YDS'].fillna(0) / 10 + df['REC'].fillna(0)) / df['touches'],
            0
        )
        df['fantasy_per_touch'] = df['fantasy_per_touch'].round(2)
    
    return df


def calculate_wr_te_advanced_metrics(wr_te_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate advanced WR/TE metrics from FantasyPros data.
    
    Metrics:
    - Target Quality Score: AIR/TGT (average depth of target)
    - Catchable Rate: CATCHABLE / TGT (QB accuracy to this player)
    - Drop Rate: DROP / CATCHABLE
    - Separation Score: YAC/R relative to position average
    - Route Efficiency: YDS / AIR (how much gained vs targeted)
    - Contact Balance: YACON/REC (yards after contact per catch)
    - Broken Tackle Rate: BRKTKL / REC
    - Red Zone Target Share: RZ TGT / TGT
    - Big Play Rate: (30+ YDS + 40+ YDS + 50+ YDS) / REC
    - Team Target Share: % TM (already provided)
    
    Args:
        wr_te_df: DataFrame with WR/TE stats from FantasyPros
    
    Returns:
        DataFrame with added advanced metric columns
    """
    df = wr_te_df.copy()
    
    # Target Quality Score (depth of target)
    if all(col in df.columns for col in ['AIR', 'TGT']):
        df['target_quality'] = np.where(
            df['TGT'] > 0,
            df['AIR'].fillna(0) / df['TGT'],
            0
        )
        df['target_quality'] = df['target_quality'].round(2)
    
    # Catchable Rate (QB accuracy)
    if all(col in df.columns for col in ['CATCHABLE', 'TGT']):
        df['catchable_rate'] = np.where(
            df['TGT'] > 0,
            df['CATCHABLE'].fillna(0) / df['TGT'],
            0
        )
        df['catchable_rate'] = df['catchable_rate'].clip(0, 1).round(3)
    
    # Drop Rate (player hands)
    if all(col in df.columns for col in ['DROP', 'CATCHABLE']):
        df['drop_rate'] = np.where(
            df['CATCHABLE'] > 0,
            df['DROP'].fillna(0) / df['CATCHABLE'],
            0
        )
        df['drop_rate'] = df['drop_rate'].clip(0, 1).round(3)
    
    # Route Efficiency (yards gained vs air yards)
    if all(col in df.columns for col in ['YDS', 'AIR']):
        df['route_efficiency'] = np.where(
            df['AIR'] > 0,
            df['YDS'].fillna(0) / df['AIR'],
            1.0  # Default to 1.0 if no air yards (short routes)
        )
        df['route_efficiency'] = df['route_efficiency'].round(3)
    
    # YAC per Reception (already provided as YAC/R)
    # Keep original or calculate
    if 'YAC/R' not in df.columns and all(col in df.columns for col in ['YAC', 'REC']):
        df['yac_per_rec'] = np.where(
            df['REC'] > 0,
            df['YAC'].fillna(0) / df['REC'],
            0
        )
        df['yac_per_rec'] = df['yac_per_rec'].round(2)
    else:
        df['yac_per_rec'] = df['YAC/R'].fillna(0).round(2)
    
    # Contact Balance: YACON per reception
    if all(col in df.columns for col in ['YACON', 'REC']):
        df['contact_balance'] = np.where(
            df['REC'] > 0,
            df['YACON'].fillna(0) / df['REC'],
            0
        )
        df['contact_balance'] = df['contact_balance'].round(2)
    
    # Broken Tackle Rate per reception
    if all(col in df.columns for col in ['BRKTKL', 'REC']):
        df['broken_tackle_rate'] = np.where(
            df['REC'] > 0,
            df['BRKTKL'].fillna(0) / df['REC'],
            0
        )
        df['broken_tackle_rate'] = df['broken_tackle_rate'].round(3)
    
    # Red Zone Target Share
    if all(col in df.columns for col in ['RZ TGT', 'TGT']):
        df['red_zone_target_share'] = np.where(
            df['TGT'] > 0,
            df['RZ TGT'].fillna(0) / df['TGT'],
            0
        )
        df['red_zone_target_share'] = df['red_zone_target_share'].round(3)
    
    # Big Play Rate
    big_play_cols = ['30+ YDS', '40+ YDS', '50+ YDS']
    existing_cols = [col for col in big_play_cols if col in df.columns]
    if existing_cols and 'REC' in df.columns:
        df['big_plays'] = df[existing_cols].fillna(0).sum(axis=1)
        df['big_play_rate'] = np.where(
            df['REC'] > 0,
            df['big_plays'] / df['REC'],
            0
        )
        df['big_play_rate'] = df['big_play_rate'].round(3)
    
    # Catch Rate (already can be calculated as REC/TGT)
    if all(col in df.columns for col in ['REC', 'TGT']):
        df['catch_rate'] = np.where(
            df['TGT'] > 0,
            df['REC'].fillna(0) / df['TGT'],
            0
        )
        df['catch_rate'] = df['catch_rate'].clip(0, 1).round(3)
    
    return df


def calculate_position_relative_metrics(df: pd.DataFrame, position: str) -> pd.DataFrame:
    """
    Calculate position-relative metrics (vs league average).
    
    Compares player stats to position average for:
    - WR/TE: YAC/R vs average (separation score)
    - RB: Contact efficiency vs average
    - QB: Pressure rate vs average
    
    Args:
        df: DataFrame with advanced metrics already calculated
        position: Position code ('QB', 'RB', 'WR', 'TE')
    
    Returns:
        DataFrame with position-relative columns added
    """
    result = df.copy()
    
    # Calculate weekly position averages
    if 'Week' in result.columns:
        for week in result['Week'].unique():
            week_data = result[result['Week'] == week]
            
            if position in ['WR', 'TE'] and 'yac_per_rec' in result.columns:
                pos_avg = week_data['yac_per_rec'].mean()
                result.loc[result['Week'] == week, 'yac_vs_avg'] = (
                    result.loc[result['Week'] == week, 'yac_per_rec'] - pos_avg
                ).round(2)
            
            if position == 'RB' and 'contact_efficiency' in result.columns:
                pos_avg = week_data['contact_efficiency'].mean()
                result.loc[result['Week'] == week, 'contact_eff_vs_avg'] = (
                    result.loc[result['Week'] == week, 'contact_efficiency'] - pos_avg
                ).round(2)
            
            if position == 'QB' and 'pressure_rate' in result.columns:
                pos_avg = week_data['pressure_rate'].mean()
                result.loc[result['Week'] == week, 'pressure_vs_avg'] = (
                    result.loc[result['Week'] == week, 'pressure_rate'] - pos_avg
                ).round(3)
    
    return result


def add_all_advanced_metrics(fp_data: pd.DataFrame) -> pd.DataFrame:
    """
    Add all position-specific advanced metrics to FantasyPros data.
    
    Args:
        fp_data: Combined FantasyPros data from load_fantasypros_data()
    
    Returns:
        DataFrame with all advanced metrics added
    """
    result_dfs = []
    
    for position in fp_data['Position'].unique():
        pos_data = fp_data[fp_data['Position'] == position].copy()
        
        if position == 'QB':
            pos_data = calculate_qb_advanced_metrics(pos_data)
            pos_data = calculate_position_relative_metrics(pos_data, 'QB')
        elif position == 'RB':
            pos_data = calculate_rb_advanced_metrics(pos_data)
            pos_data = calculate_position_relative_metrics(pos_data, 'RB')
        elif position in ['WR', 'TE']:
            pos_data = calculate_wr_te_advanced_metrics(pos_data)
            pos_data = calculate_position_relative_metrics(pos_data, position)
        
        result_dfs.append(pos_data)
    
    return pd.concat(result_dfs, ignore_index=True)


# Testing and example usage
if __name__ == "__main__":
    # Import correlation_model for data loading
    from correlation_model import load_fantasypros_data
    
    print("=" * 70)
    print("ADVANCED METRICS FEATURE ENGINEERING TEST")
    print("=" * 70)
    
    print("\n1. Loading FantasyPros data...")
    fp_data = load_fantasypros_data()
    print(f"   ✓ Loaded {len(fp_data)} player-week records")
    
    print("\n2. Adding advanced metrics...")
    enriched_data = add_all_advanced_metrics(fp_data)
    print(f"   ✓ Enriched {len(enriched_data)} records")
    
    # Show QB metrics
    print("\n3. Sample QB Advanced Metrics:")
    qb_sample = enriched_data[enriched_data['Position'] == 'QB'].head(3)
    qb_cols = ['Player', 'Team', 'Week', 'pressure_rate', 'deep_ball_rate', 'accuracy_score']
    if all(col in qb_sample.columns for col in qb_cols):
        print(qb_sample[qb_cols].to_string(index=False))
    
    # Show RB metrics
    print("\n4. Sample RB Advanced Metrics:")
    rb_sample = enriched_data[enriched_data['Position'] == 'RB'].head(3)
    rb_cols = ['Player', 'Team', 'Week', 'contact_efficiency', 'broken_tackle_rate', 'receiving_back_score']
    if all(col in rb_sample.columns for col in rb_cols):
        print(rb_sample[rb_cols].to_string(index=False))
    
    # Show WR metrics
    print("\n5. Sample WR Advanced Metrics:")
    wr_sample = enriched_data[enriched_data['Position'] == 'WR'].head(3)
    wr_cols = ['Player', 'Team', 'Week', 'target_quality', 'catchable_rate', 'yac_per_rec']
    if all(col in wr_sample.columns for col in wr_cols):
        print(wr_sample[wr_cols].to_string(index=False))
    
    # Show summary statistics
    print("\n6. Metric Summary Statistics:")
    
    if 'pressure_rate' in enriched_data.columns:
        qb_data = enriched_data[enriched_data['Position'] == 'QB']
        print(f"\n   QB Pressure Rate:")
        print(f"   - Mean: {qb_data['pressure_rate'].mean():.3f}")
        print(f"   - Median: {qb_data['pressure_rate'].median():.3f}")
        print(f"   - Range: {qb_data['pressure_rate'].min():.3f} to {qb_data['pressure_rate'].max():.3f}")
    
    if 'broken_tackle_rate' in enriched_data.columns:
        rb_data = enriched_data[enriched_data['Position'] == 'RB']
        print(f"\n   RB Broken Tackle Rate:")
        print(f"   - Mean: {rb_data['broken_tackle_rate'].mean():.3f}")
        print(f"   - Median: {rb_data['broken_tackle_rate'].median():.3f}")
        print(f"   - Range: {rb_data['broken_tackle_rate'].min():.3f} to {rb_data['broken_tackle_rate'].max():.3f}")
    
    if 'target_quality' in enriched_data.columns:
        wr_data = enriched_data[enriched_data['Position'] == 'WR']
        print(f"\n   WR Target Quality (depth):")
        print(f"   - Mean: {wr_data['target_quality'].mean():.2f} yards")
        print(f"   - Median: {wr_data['target_quality'].median():.2f} yards")
        print(f"   - Range: {wr_data['target_quality'].min():.2f} to {wr_data['target_quality'].max():.2f} yards")
    
    print("\n" + "=" * 70)
    print("✅ Feature engineering test complete!")
    print("=" * 70)
    
    print("\n📊 Metrics Added:")
    print("   QB: pressure_rate, deep_ball_rate, accuracy_score, big_play_rate")
    print("   RB: contact_efficiency, broken_tackle_rate, receiving_back_score")
    print("   WR/TE: target_quality, catchable_rate, drop_rate, yac_per_rec")
