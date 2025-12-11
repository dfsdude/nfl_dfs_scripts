"""
Correlation Model Module

Computes within-team player correlations using FantasyPros advanced stats data.
Produces correlation metrics for stacking analysis:
- QB ↔ WR1/WR2/TE1 correlations
- WR1 ↔ WR2/TE1 correlations
- RB1 ↔ WR1 correlations

Usage:
    from correlation_model import (
        load_fantasypros_data,
        build_team_player_roles,
        compute_team_correlations,
        compute_team_correlations_by_week
    )
    
    fp_data = load_fantasypros_data()
    roles_df = build_team_player_roles(fp_data)
    season_corr = compute_team_correlations(fp_data, roles_df)
    rolling_corr = compute_team_correlations_by_week(fp_data, roles_df, lookback=5)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict
import os


def load_fantasypros_data(
    fantasypros_dir: Optional[Path] = None,
    weeks: Optional[list] = None
) -> pd.DataFrame:
    """
    Load FantasyPros advanced stats for all positions and prepare for correlation analysis.
    
    Args:
        fantasypros_dir: Path to FantasyPros data directory (defaults to data/fantasypros/)
        weeks: Optional list of weeks to filter (e.g., [1, 2, 3])
    
    Returns:
        Combined DataFrame with columns:
            - Player: Player name (normalized, without team suffix)
            - Position: QB, RB, WR, TE
            - Team: Team abbreviation
            - Week: Week number (integer)
            - DK_Points: Fantasy points proxy (calculated from stats)
            - Plus all original FantasyPros stats
    """
    if fantasypros_dir is None:
        fantasypros_dir = Path(__file__).parent / "data" / "fantasypros"
    
    position_files = {
        'QB': 'QB_Advanced_Stats_2025.csv',
        'RB': 'RB_Advanced_Stats_2025.csv',
        'WR': 'WR_Advanced_Stats_2025.csv',
        'TE': 'TE_Advanced_Stats_2025.csv'
    }
    
    dfs = []
    
    for position, filename in position_files.items():
        filepath = fantasypros_dir / filename
        
        if not filepath.exists():
            print(f"⚠ Warning: {filename} not found, skipping {position}")
            continue
        
        # Load CSV
        df = pd.read_csv(filepath)
        
        # Extract week number from "Week X" format
        df['week_num'] = df['Week'].str.extract(r'Week (\d+)', expand=False).astype(int)
        
        # Extract team from Player column (e.g., "Josh Allen(BUF)" -> "BUF")
        df['team'] = df['Player'].str.extract(r'\(([A-Z]{2,3})\)', expand=False)
        
        # Normalize player name (remove team suffix)
        df['player_clean'] = df['Player'].str.replace(r'\([A-Z]{2,3}\)', '', regex=True).str.strip()
        
        # Add position column
        df['position'] = position
        
        # Filter weeks if specified
        if weeks:
            df = df[df['week_num'].isin(weeks)]
        
        # Calculate DK_Points proxy based on position
        if position == 'QB':
            # QB scoring: Pass YDS/25 + Pass TD*4 + INT*-1 + Rush YDS/10 + Rush TD*6
            # Approximate using available stats
            df['dk_points'] = (
                df['YDS'].fillna(0) / 25 +  # Passing yards
                df['RTG'].fillna(0) / 30  # Rating as proxy for TDs (rough estimate)
            )
        elif position == 'RB':
            # RB scoring: Rush YDS/10 + Rush TD*6 + Rec*1 + Rec YDS/10 + Rec TD*6
            df['dk_points'] = (
                df['YDS'].fillna(0) / 10 +  # Rushing yards
                df['REC'].fillna(0)  # Receptions (PPR)
            )
        elif position in ['WR', 'TE']:
            # WR/TE scoring: Rec*1 + Rec YDS/10 + Rec TD*6
            df['dk_points'] = (
                df['REC'].fillna(0) +  # Receptions (PPR)
                df['YDS'].fillna(0) / 10  # Receiving yards
            )
        
        dfs.append(df)
    
    # Combine all positions
    combined = pd.concat(dfs, ignore_index=True)
    
    # Drop original Week and Player columns to avoid duplicates after rename
    cols_to_drop = []
    if 'Week' in combined.columns and 'week_num' in combined.columns:
        cols_to_drop.append('Week')
    # IMPORTANT: Drop the original Player column (with team suffix) before rename
    if 'Player' in combined.columns and 'player_clean' in combined.columns:
        cols_to_drop.append('Player')
    
    if cols_to_drop:
        combined = combined.drop(columns=cols_to_drop)
    
    # Rename columns for consistency with old format
    combined = combined.rename(columns={
        'player_clean': 'Player',
        'position': 'Position',
        'team': 'Team',
        'week_num': 'Week',
        'dk_points': 'DK_Points'
    })
    
    # Remove duplicate columns if they exist
    combined = combined.loc[:, ~combined.columns.duplicated()]
    
    # Handle NaN teams (should be rare)
    combined = combined.dropna(subset=['Team', 'Player', 'Week'])
    
    return combined


def build_team_player_roles(weekly_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Identify key players (QB1, WR1, WR2, TE1, RB1) for each team.
    
    Uses FantasyPros advanced stats for ranking:
    - QB1: Most Pass Attempts (ATT)
    - WR1/WR2: Most/Second-most Targets (TGT)
    - TE1: Most Targets among TEs (TGT)
    - RB1: Most touches (ATT + REC for RBs, TGT for WR/TE)
    
    Args:
        weekly_stats: DataFrame from load_fantasypros_data() with columns:
            - Player, Position, Team, Week
            - For QB: ATT (pass attempts)
            - For RB: ATT (rush attempts), TGT (targets), REC
            - For WR/TE: TGT (targets), REC
    
    Returns:
        DataFrame with columns: Team, QB1, WR1, WR2, TE1, RB1
        Each value is the player name in that role
    """
    roles = []
    
    for team in weekly_stats['Team'].unique():
        team_data = weekly_stats[weekly_stats['Team'] == team].copy()
        
        role_dict = {'Team': team}
        
        # QB1: Most Pass Attempts (ATT column for QBs)
        qbs = team_data[team_data['Position'] == 'QB'].copy()
        if len(qbs) > 0 and 'ATT' in qbs.columns:
            qb_totals = qbs.groupby('Player')['ATT'].sum().sort_values(ascending=False)
            role_dict['QB1'] = qb_totals.index[0] if len(qb_totals) > 0 else None
        else:
            role_dict['QB1'] = None
        
        # WR1, WR2: Top 2 by Targets (TGT)
        wrs = team_data[team_data['Position'] == 'WR'].copy()
        if len(wrs) > 0 and 'TGT' in wrs.columns:
            wr_totals = wrs.groupby('Player')['TGT'].sum().sort_values(ascending=False)
            role_dict['WR1'] = wr_totals.index[0] if len(wr_totals) > 0 else None
            role_dict['WR2'] = wr_totals.index[1] if len(wr_totals) > 1 else None
        else:
            role_dict['WR1'] = None
            role_dict['WR2'] = None
        
        # TE1: Most Targets among TEs (TGT)
        tes = team_data[team_data['Position'] == 'TE'].copy()
        if len(tes) > 0 and 'TGT' in tes.columns:
            te_totals = tes.groupby('Player')['TGT'].sum().sort_values(ascending=False)
            role_dict['TE1'] = te_totals.index[0] if len(te_totals) > 0 else None
        else:
            role_dict['TE1'] = None
        
        # RB1: Most touches (ATT + REC for RBs)
        rbs = team_data[team_data['Position'] == 'RB'].copy()
        if len(rbs) > 0:
            if 'ATT' in rbs.columns and 'REC' in rbs.columns:
                rbs['rb_touches'] = rbs['ATT'].fillna(0) + rbs['REC'].fillna(0)
                rb_totals = rbs.groupby('Player')['rb_touches'].sum().sort_values(ascending=False)
            elif 'ATT' in rbs.columns:
                rb_totals = rbs.groupby('Player')['ATT'].sum().sort_values(ascending=False)
            elif 'TGT' in rbs.columns:
                rb_totals = rbs.groupby('Player')['TGT'].sum().sort_values(ascending=False)
            else:
                rb_totals = pd.Series()
            
            role_dict['RB1'] = rb_totals.index[0] if len(rb_totals) > 0 else None
        else:
            role_dict['RB1'] = None
        
        roles.append(role_dict)
    
    return pd.DataFrame(roles)


def compute_team_correlations(
    weekly_stats: pd.DataFrame,
    roles_df: pd.DataFrame,
    min_weeks: int = 3
) -> pd.DataFrame:
    """
    Compute season-level correlations between key players for each team.
    
    Calculates correlations using full-season DK_Points data:
    - QB ↔ WR1, WR2, TE1
    - WR1 ↔ WR2, TE1
    - RB1 ↔ WR1
    
    Args:
        weekly_stats: DataFrame with Player, Position, Team, Week, DK_Points
        roles_df: Output from build_team_player_roles()
        min_weeks: Minimum weeks of data required to compute correlation
    
    Returns:
        DataFrame with columns:
            - Team
            - corr_qb_wr1, corr_qb_wr2, corr_qb_te1
            - corr_wr1_wr2, corr_wr1_te1, corr_rb1_wr1
    """
    correlations = []
    
    for _, role_row in roles_df.iterrows():
        team = role_row['Team']
        team_data = weekly_stats[weekly_stats['Team'] == team].copy()
        
        # Pivot to wide format: rows=Week, columns=Player, values=DK_Points
        pivot_df = team_data.pivot_table(
            index='Week',
            columns='Player',
            values='DK_Points',
            aggfunc='sum'
        ).fillna(0)
        
        # Need at least min_weeks of data
        if len(pivot_df) < min_weeks:
            continue
        
        # Compute correlation matrix
        corr_matrix = pivot_df.corr()
        
        # Extract correlations for key pairs
        corr_dict = {'Team': team}
        
        # Helper function to safely get correlation
        def get_corr(player1, player2):
            if player1 and player2 and player1 in corr_matrix.index and player2 in corr_matrix.columns:
                val = corr_matrix.loc[player1, player2]
                return round(val, 3) if not pd.isna(val) else None
            return None
        
        # QB correlations
        corr_dict['corr_qb_wr1'] = get_corr(role_row['QB1'], role_row['WR1'])
        corr_dict['corr_qb_wr2'] = get_corr(role_row['QB1'], role_row['WR2'])
        corr_dict['corr_qb_te1'] = get_corr(role_row['QB1'], role_row['TE1'])
        corr_dict['corr_qb_rb1'] = get_corr(role_row['QB1'], role_row['RB1'])
        
        # Pass catcher correlations
        corr_dict['corr_wr1_wr2'] = get_corr(role_row['WR1'], role_row['WR2'])
        corr_dict['corr_wr1_te1'] = get_corr(role_row['WR1'], role_row['TE1'])
        corr_dict['corr_wr2_te1'] = get_corr(role_row['WR2'], role_row['TE1'])
        
        # RB correlations
        corr_dict['corr_rb1_wr1'] = get_corr(role_row['RB1'], role_row['WR1'])
        corr_dict['corr_rb1_wr2'] = get_corr(role_row['RB1'], role_row['WR2'])
        
        # Add player names for reference
        corr_dict['QB1'] = role_row['QB1']
        corr_dict['WR1'] = role_row['WR1']
        corr_dict['WR2'] = role_row['WR2']
        corr_dict['TE1'] = role_row['TE1']
        corr_dict['RB1'] = role_row['RB1']
        
        correlations.append(corr_dict)
    
    return pd.DataFrame(correlations)


def compute_team_correlations_by_week(
    weekly_stats: pd.DataFrame,
    roles_df: pd.DataFrame,
    lookback: int = 5
) -> pd.DataFrame:
    """
    Compute rolling correlations over a lookback window for each team-week.
    
    For each week W, calculates correlations using data from weeks [W-lookback+1, W].
    
    Args:
        weekly_stats: DataFrame with Player, Position, Team, Week, DK_Points
        roles_df: Output from build_team_player_roles()
        lookback: Number of weeks to include in rolling window (default: 5)
    
    Returns:
        DataFrame with columns:
            - Team, Week
            - corr_qb_wr1_last{lookback}, corr_qb_wr2_last{lookback}, etc.
    """
    rolling_correlations = []
    
    for _, role_row in roles_df.iterrows():
        team = role_row['Team']
        team_data = weekly_stats[weekly_stats['Team'] == team].copy()
        
        # Pivot to wide format
        pivot_df = team_data.pivot_table(
            index='Week',
            columns='Player',
            values='DK_Points',
            aggfunc='sum'
        ).fillna(0).sort_index()
        
        # Need at least lookback weeks
        if len(pivot_df) < lookback:
            continue
        
        # Get all weeks
        weeks = sorted(pivot_df.index.unique())
        
        # For each week starting from lookback
        for i in range(lookback - 1, len(weeks)):
            current_week = weeks[i]
            start_week = weeks[max(0, i - lookback + 1)]
            
            # Get windowed data
            window_df = pivot_df.loc[start_week:current_week]
            
            # Compute correlation for this window
            if len(window_df) < 3:  # Need at least 3 weeks for meaningful correlation
                continue
            
            corr_matrix = window_df.corr()
            
            # Extract correlations
            corr_dict = {'Team': team, 'Week': current_week}
            
            # Helper function to safely get correlation
            def get_corr(player1, player2):
                if player1 and player2 and player1 in corr_matrix.index and player2 in corr_matrix.columns:
                    val = corr_matrix.loc[player1, player2]
                    return round(val, 3) if not pd.isna(val) else None
                return None
            
            # QB correlations
            corr_dict[f'corr_qb_wr1_last{lookback}'] = get_corr(role_row['QB1'], role_row['WR1'])
            corr_dict[f'corr_qb_wr2_last{lookback}'] = get_corr(role_row['QB1'], role_row['WR2'])
            corr_dict[f'corr_qb_te1_last{lookback}'] = get_corr(role_row['QB1'], role_row['TE1'])
            corr_dict[f'corr_qb_rb1_last{lookback}'] = get_corr(role_row['QB1'], role_row['RB1'])
            
            # Pass catcher correlations
            corr_dict[f'corr_wr1_wr2_last{lookback}'] = get_corr(role_row['WR1'], role_row['WR2'])
            corr_dict[f'corr_wr1_te1_last{lookback}'] = get_corr(role_row['WR1'], role_row['TE1'])
            
            # RB correlations
            corr_dict[f'corr_rb1_wr1_last{lookback}'] = get_corr(role_row['RB1'], role_row['WR1'])
            
            rolling_correlations.append(corr_dict)
    
    return pd.DataFrame(rolling_correlations)


def get_correlation_label(corr: Optional[float]) -> str:
    """
    Classify correlation strength into descriptive labels.
    
    Args:
        corr: Correlation value between -1 and 1
    
    Returns:
        Label: "Strong Positive", "Moderate Positive", "Weak/None", 
               "Moderate Negative", "Strong Negative"
    """
    if corr is None or pd.isna(corr):
        return "No Data"
    
    if corr >= 0.5:
        return "Strong Positive"
    elif corr >= 0.2:
        return "Moderate Positive"
    elif corr >= -0.2:
        return "Weak/None"
    elif corr >= -0.5:
        return "Moderate Negative"
    else:
        return "Strong Negative"


def get_correlation_rag(corr: Optional[float]) -> str:
    """
    Get RAG indicator for correlation strength (for stacking purposes).
    
    High positive correlation = good for stacking (🟢)
    Near zero = neutral (🟡)
    Negative correlation = bad for stacking (🔴)
    
    Args:
        corr: Correlation value between -1 and 1
    
    Returns:
        RAG indicator: 🟢 (high positive), 🟡 (neutral), 🔴 (negative)
    """
    if corr is None or pd.isna(corr):
        return '⚪'
    
    if corr >= 0.4:
        return '🟢'
    elif corr >= -0.2:
        return '🟡'
    else:
        return '🔴'


# Example usage and testing
if __name__ == "__main__":
    # Example: Load FantasyPros data and compute correlations
    import os
    
    print("=" * 70)
    print("CORRELATION MODEL - FANTASYPROS DATA TEST")
    print("=" * 70)
    
    print("\n1. Loading FantasyPros advanced stats...")
    fp_data = load_fantasypros_data()
    print(f"   ✓ Loaded {len(fp_data)} player-week records")
    print(f"   ✓ Weeks: {fp_data['Week'].min()} to {fp_data['Week'].max()}")
    print(f"   ✓ Teams: {fp_data['Team'].nunique()} teams")
    print(f"   ✓ Positions: {', '.join(fp_data['Position'].unique())}")
    
    print("\n2. Building team player roles...")
    roles_df = build_team_player_roles(fp_data)
    print(f"   ✓ Found roles for {len(roles_df)} teams")
    print("\n   Sample roles (first 3 teams):")
    print(roles_df[['Team', 'QB1', 'WR1', 'WR2', 'TE1', 'RB1']].head(3).to_string(index=False))
    
    print("\n3. Computing season-level correlations...")
    season_corr = compute_team_correlations(fp_data, roles_df, min_weeks=4)
    print(f"   ✓ Computed correlations for {len(season_corr)} teams")
    print("\n   Sample correlations:")
    if len(season_corr) > 0:
        print(season_corr[['Team', 'QB1', 'WR1', 'corr_qb_wr1', 'corr_wr1_wr2']].head(5).to_string(index=False))
    
    print("\n4. Computing rolling 5-week correlations...")
    rolling_corr = compute_team_correlations_by_week(fp_data, roles_df, lookback=5)
    print(f"   ✓ Computed {len(rolling_corr)} team-week correlation records")
    if len(rolling_corr) > 0:
        print("\n   Sample rolling correlations:")
        print(rolling_corr[['Team', 'Week', 'corr_qb_wr1_last5']].head(10).to_string(index=False))
    
    # Show correlation strength distribution
    if len(season_corr) > 0:
        print("\n5. Correlation strength analysis (QB-WR1):")
        qb_wr1_corrs = season_corr['corr_qb_wr1'].dropna()
        if len(qb_wr1_corrs) > 0:
            print(f"   Mean: {qb_wr1_corrs.mean():.3f}")
            print(f"   Median: {qb_wr1_corrs.median():.3f}")
            print(f"   Std Dev: {qb_wr1_corrs.std():.3f}")
            print(f"   Range: {qb_wr1_corrs.min():.3f} to {qb_wr1_corrs.max():.3f}")
            
            # Count by strength
            strong_pos = (qb_wr1_corrs >= 0.5).sum()
            moderate_pos = ((qb_wr1_corrs >= 0.2) & (qb_wr1_corrs < 0.5)).sum()
            weak = ((qb_wr1_corrs >= -0.2) & (qb_wr1_corrs < 0.2)).sum()
            negative = (qb_wr1_corrs < -0.2).sum()
            
            print(f"\n   Distribution:")
            print(f"   - Strong Positive (≥0.5): {strong_pos}")
            print(f"   - Moderate Positive (0.2-0.5): {moderate_pos}")
            print(f"   - Weak/None (-0.2 to 0.2): {weak}")
            print(f"   - Negative (<-0.2): {negative}")
    
    print("\n" + "=" * 70)
    print("✅ Correlation module test complete!")
    print("=" * 70)
    
    # Show data source info
    print("\n📊 Data Source:")
    print("   Using FantasyPros Advanced Stats (data/fantasypros/)")
    print("   Week-by-week granularity for accurate correlations")
    print("   Role detection based on actual usage (ATT, TGT, REC)")
    
    # Backward compatibility note
    print("\n💡 Legacy Compatibility:")
    print("   The module accepts any DataFrame with columns:")
    print("   - Player, Position, Team, Week, DK_Points")
    print("   Can still use Weekly_Stats.csv if passed to functions")
