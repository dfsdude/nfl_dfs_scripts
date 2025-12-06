"""
Correlation Model Module

Computes within-team player correlations using weekly_stats.csv data.
Produces correlation metrics for stacking analysis:
- QB ↔ WR1/WR2/TE1 correlations
- WR1 ↔ WR2/TE1 correlations
- RB1 ↔ WR1 correlations

Usage:
    from correlation_model import (
        build_team_player_roles,
        compute_team_correlations,
        compute_team_correlations_by_week
    )
    
    roles_df = build_team_player_roles(weekly_stats)
    season_corr = compute_team_correlations(weekly_stats, roles_df)
    rolling_corr = compute_team_correlations_by_week(weekly_stats, roles_df, lookback=5)
"""

import pandas as pd
import numpy as np
from typing import Optional


def build_team_player_roles(weekly_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Identify key players (QB1, WR1, WR2, TE1, RB1) for each team.
    
    Uses the following ranking criteria:
    - QB1: Most Pass_Att
    - WR1/WR2: Most/Second-most Targets
    - TE1: Most Targets among TEs
    - RB1: Most Weighted_Opportunities (or Rush_Att + Targets)
    
    Args:
        weekly_stats: DataFrame with columns including:
            - Player, Position, Team, Week
            - Pass_Att, Targets, Rush_Att, Weighted_Opportunities
    
    Returns:
        DataFrame with columns: Team, QB1, WR1, WR2, TE1, RB1
        Each value is the player name in that role
    """
    roles = []
    
    for team in weekly_stats['Team'].unique():
        team_data = weekly_stats[weekly_stats['Team'] == team].copy()
        
        role_dict = {'Team': team}
        
        # QB1: Most Pass_Att
        qbs = team_data[team_data['Position'] == 'QB'].copy()
        if len(qbs) > 0:
            qb_totals = qbs.groupby('Player')['Pass_Att'].sum().sort_values(ascending=False)
            role_dict['QB1'] = qb_totals.index[0] if len(qb_totals) > 0 else None
        else:
            role_dict['QB1'] = None
        
        # WR1, WR2: Top 2 by Targets
        wrs = team_data[team_data['Position'] == 'WR'].copy()
        if len(wrs) > 0:
            wr_totals = wrs.groupby('Player')['Targets'].sum().sort_values(ascending=False)
            role_dict['WR1'] = wr_totals.index[0] if len(wr_totals) > 0 else None
            role_dict['WR2'] = wr_totals.index[1] if len(wr_totals) > 1 else None
        else:
            role_dict['WR1'] = None
            role_dict['WR2'] = None
        
        # TE1: Most Targets among TEs
        tes = team_data[team_data['Position'] == 'TE'].copy()
        if len(tes) > 0:
            te_totals = tes.groupby('Player')['Targets'].sum().sort_values(ascending=False)
            role_dict['TE1'] = te_totals.index[0] if len(te_totals) > 0 else None
        else:
            role_dict['TE1'] = None
        
        # RB1: Most Weighted_Opportunities (or Rush_Att + Targets if WO missing)
        rbs = team_data[team_data['Position'] == 'RB'].copy()
        if len(rbs) > 0:
            if 'Weighted_Opportunities' in rbs.columns:
                rb_totals = rbs.groupby('Player')['Weighted_Opportunities'].sum().sort_values(ascending=False)
            else:
                # Fallback: Rush_Att + Targets
                rbs['rb_opportunities'] = rbs['Rush_Att'].fillna(0) + rbs['Targets'].fillna(0)
                rb_totals = rbs.groupby('Player')['rb_opportunities'].sum().sort_values(ascending=False)
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
    # Example: Load weekly stats and compute correlations
    import os
    
    # Assuming weekly_stats.csv is in the data directory
    data_dir = os.getenv("DFS_DATA_DIR", r"C:\Users\schne\Documents\DFS\2025\Dashboard")
    weekly_stats_path = os.path.join(data_dir, "Weekly_Stats.csv")
    
    if os.path.exists(weekly_stats_path):
        print("Loading Weekly_Stats.csv...")
        weekly_stats = pd.read_csv(weekly_stats_path)
        
        print("\n1. Building team player roles...")
        roles_df = build_team_player_roles(weekly_stats)
        print(f"   Found roles for {len(roles_df)} teams")
        print("\nSample roles:")
        print(roles_df.head(3))
        
        print("\n2. Computing season-level correlations...")
        season_corr = compute_team_correlations(weekly_stats, roles_df)
        print(f"   Computed correlations for {len(season_corr)} teams")
        print("\nSample correlations:")
        print(season_corr[['Team', 'QB1', 'WR1', 'corr_qb_wr1', 'corr_wr1_wr2']].head(5))
        
        print("\n3. Computing rolling 5-week correlations...")
        rolling_corr = compute_team_correlations_by_week(weekly_stats, roles_df, lookback=5)
        print(f"   Computed {len(rolling_corr)} team-week correlation records")
        print("\nSample rolling correlations:")
        print(rolling_corr[['Team', 'Week', 'corr_qb_wr1_last5']].head(10))
        
        print("\n✅ Correlation module test complete!")
    else:
        print(f"❌ Weekly_Stats.csv not found at: {weekly_stats_path}")
