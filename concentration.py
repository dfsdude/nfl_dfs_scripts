"""
concentration.py

Compute offensive concentration and correlation metrics for NFL teams.

This module quantifies:
- How concentrated a team's offense is (passing & rushing)
- How concentrated usage is across specific players (WR1/WR2/RB1/TE1)
- How correlated key teammates are with each other over time

Uses nflreadpy for participation and opportunity data.

Requirements:
    pip install nflreadpy pandas numpy
"""

import numpy as np
import pandas as pd
import nflreadpy as nfl
from pathlib import Path
from typing import Optional


# ---------------------------------------------------
# 1. Load External Concentration Data Sources
# ---------------------------------------------------

def load_external_concentration_sources(
    seasons: list[int] | int,
    cache_dir: Optional[str] = None
) -> dict[str, pd.DataFrame]:
    """
    Load participation and FF opportunity data from nflreadpy.
    
    Args:
        seasons: Single season (int) or list of seasons to load
        cache_dir: Optional directory to cache CSV files
        
    Returns:
        Dictionary with 'participation' and 'ff_opportunity' DataFrames
    """
    if cache_dir:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
    
    # Load participation data (routes, snaps)
    print(f"Loading participation data for seasons {seasons}...")
    participation_pl = nfl.load_participation(seasons=seasons)
    participation = participation_pl.to_pandas()
    
    if cache_dir:
        participation.to_csv(cache_path / f"participation_{seasons}.csv", index=False)
    
    # Load FF opportunity data (air yards, WOPR, xFP)
    print(f"Loading FF opportunity data for seasons {seasons}...")
    ff_opp_pl = nfl.load_ff_opportunity(seasons=seasons)
    ff_opp = ff_opp_pl.to_pandas()
    
    if cache_dir:
        ff_opp.to_csv(cache_path / f"ff_opportunity_{seasons}.csv", index=False)
    
    return {
        "participation": participation,
        "ff_opportunity": ff_opp,
    }


def load_cached_concentration_sources(
    cache_dir: str,
    seasons: list[int] | int
) -> dict[str, pd.DataFrame]:
    """
    Load concentration data from cached CSV files.
    
    Args:
        cache_dir: Directory containing cached CSV files
        seasons: Season identifier for filename
        
    Returns:
        Dictionary with 'participation' and 'ff_opportunity' DataFrames
    """
    cache_path = Path(cache_dir)
    
    participation = pd.read_csv(cache_path / f"participation_{seasons}.csv")
    ff_opp = pd.read_csv(cache_path / f"ff_opportunity_{seasons}.csv")
    
    return {
        "participation": participation,
        "ff_opportunity": ff_opp,
    }


# ---------------------------------------------------
# 2. Build Weekly Player Usage Table
# ---------------------------------------------------

def build_weekly_player_usage(
    participation: pd.DataFrame,
    ff_opp: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge participation and FF opportunity data into unified weekly usage table.
    
    Args:
        participation: Participation DataFrame with routes, snaps
        ff_opp: FF opportunity DataFrame with air yards, WOPR, xFP
        
    Returns:
        DataFrame with weekly player usage metrics
    """
    # Select and rename relevant columns from participation
    part_cols = [
        'season', 'week', 'game_id', 'team', 'player_id', 'player_name',
        'n_offense_snaps', 'n_pass_snaps', 'n_routes', 
        'n_targets', 'n_rush_att'
    ]
    
    # Filter to only columns that exist
    part_cols_available = [col for col in part_cols if col in participation.columns]
    part_subset = participation[part_cols_available].copy()
    
    # Select relevant columns from ff_opportunity
    ff_cols = [
        'season', 'week', 'player_id', 'team',
        'targets', 'air_yards', 'wopr', 'xfp'
    ]
    
    ff_cols_available = [col for col in ff_cols if col in ff_opp.columns]
    ff_subset = ff_opp[ff_cols_available].copy()
    
    # Merge on season, week, player_id, team
    merge_keys = ['season', 'week', 'player_id', 'team']
    usage_df = pd.merge(
        part_subset,
        ff_subset,
        on=merge_keys,
        how='outer'
    )
    
    # Rename columns for consistency
    rename_map = {
        'n_offense_snaps': 'offense_snaps',
        'n_pass_snaps': 'pass_snaps',
        'n_routes': 'routes_run',
        'n_targets': 'participation_targets',
        'n_rush_att': 'rush_att',
        'targets': 'ff_targets',
    }
    
    usage_df = usage_df.rename(columns=rename_map)
    
    # Consolidate targets (prefer ff_targets, fallback to participation_targets)
    if 'ff_targets' in usage_df.columns and 'participation_targets' in usage_df.columns:
        usage_df['targets'] = usage_df['ff_targets'].fillna(usage_df['participation_targets'])
    elif 'ff_targets' in usage_df.columns:
        usage_df['targets'] = usage_df['ff_targets']
    elif 'participation_targets' in usage_df.columns:
        usage_df['targets'] = usage_df['participation_targets']
    
    # Calculate RB opportunities (rush_att + targets)
    if 'rush_att' in usage_df.columns and 'targets' in usage_df.columns:
        usage_df['rb_opportunities'] = (
            usage_df['rush_att'].fillna(0) + usage_df['targets'].fillna(0)
        )
    
    # Fill NaN values with 0 for numeric columns
    numeric_cols = [
        'offense_snaps', 'pass_snaps', 'routes_run', 'targets',
        'air_yards', 'wopr', 'xfp', 'rush_att', 'rb_opportunities'
    ]
    
    for col in numeric_cols:
        if col in usage_df.columns:
            usage_df[col] = usage_df[col].fillna(0)
    
    return usage_df


# ---------------------------------------------------
# 3. Compute Team-Level Concentration Scores
# ---------------------------------------------------

def compute_herfindahl_index(shares: pd.Series) -> float:
    """
    Calculate Herfindahl-Hirschman Index (HHI) for concentration.
    
    HHI = sum of squared market shares
    Range: 1/n (perfectly distributed) to 1.0 (monopoly)
    
    Args:
        shares: Series of usage shares (should sum to ~1.0)
        
    Returns:
        HHI score (0-1, higher = more concentrated)
    """
    # Remove zeros and normalize
    shares_clean = shares[shares > 0]
    if len(shares_clean) == 0:
        return 0.0
    
    # Normalize to ensure sum = 1
    shares_norm = shares_clean / shares_clean.sum()
    
    # Calculate HHI
    hhi = (shares_norm ** 2).sum()
    
    return hhi


def compute_team_concentration(usage_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute team-level concentration scores using HHI.
    
    Calculates concentration across:
    - Target share
    - Air yards share
    - Route share
    - RB opportunity share
    
    Args:
        usage_df: Weekly player usage DataFrame
        
    Returns:
        DataFrame with team-week concentration metrics
    """
    # Group by season, week, team
    team_weekly = []
    
    for (season, week, team), group in usage_df.groupby(['season', 'week', 'team']):
        
        # Calculate shares
        total_targets = group['targets'].sum()
        total_air_yards = group['air_yards'].sum()
        total_routes = group['routes_run'].sum()
        total_rb_opp = group['rb_opportunities'].sum()
        
        metrics = {
            'season': season,
            'week': week,
            'team': team,
        }
        
        # Target concentration
        if total_targets > 0:
            target_shares = group['targets'] / total_targets
            metrics['target_hhi'] = compute_herfindahl_index(target_shares)
        else:
            metrics['target_hhi'] = 0.0
        
        # Air yards concentration
        if total_air_yards > 0:
            air_yard_shares = group['air_yards'] / total_air_yards
            metrics['air_yards_hhi'] = compute_herfindahl_index(air_yard_shares)
        else:
            metrics['air_yards_hhi'] = 0.0
        
        # Route concentration
        if total_routes > 0:
            route_shares = group['routes_run'] / total_routes
            metrics['route_hhi'] = compute_herfindahl_index(route_shares)
        else:
            metrics['route_hhi'] = 0.0
        
        # RB opportunity concentration
        if total_rb_opp > 0:
            rb_opp_shares = group['rb_opportunities'] / total_rb_opp
            metrics['rb_concentration_hhi'] = compute_herfindahl_index(rb_opp_shares)
        else:
            metrics['rb_concentration_hhi'] = 0.0
        
        # Combined pass concentration (average of target, air yards, route HHI)
        pass_hhis = [
            metrics['target_hhi'],
            metrics['air_yards_hhi'],
            metrics['route_hhi']
        ]
        metrics['pass_concentration_index'] = np.mean([h for h in pass_hhis if h > 0])
        
        # Overall concentration (weighted average: 70% pass, 30% rush)
        metrics['overall_concentration_index'] = (
            0.7 * metrics['pass_concentration_index'] +
            0.3 * metrics['rb_concentration_hhi']
        )
        
        team_weekly.append(metrics)
    
    concentration_df = pd.DataFrame(team_weekly)
    
    # Scale to 0-100 for easier interpretation
    concentration_df['pass_concentration_score'] = (
        concentration_df['pass_concentration_index'] * 100
    ).round(1)
    
    concentration_df['rb_concentration_score'] = (
        concentration_df['rb_concentration_hhi'] * 100
    ).round(1)
    
    concentration_df['overall_concentration_score'] = (
        concentration_df['overall_concentration_index'] * 100
    ).round(1)
    
    return concentration_df


# ---------------------------------------------------
# 4. RAG Status Helpers
# ---------------------------------------------------

def get_concentration_rag(score: float) -> str:
    """
    Get RAG (Red-Amber-Green) status for concentration score.
    
    High concentration (>40) = Good for stacking (🟢)
    Medium concentration (25-40) = Moderate (🟡)
    Low concentration (<25) = Risky for stacks (🔴)
    
    Args:
        score: Concentration score (0-100)
        
    Returns:
        RAG indicator emoji
    """
    if score >= 40:
        return '🟢'
    elif score >= 25:
        return '🟡'
    else:
        return '🔴'


def get_concentration_label(score: float) -> str:
    """
    Get descriptive label for concentration score.
    
    Args:
        score: Concentration score (0-100)
        
    Returns:
        Descriptive label
    """
    if score >= 40:
        return 'High'
    elif score >= 25:
        return 'Medium'
    else:
        return 'Low'


# ---------------------------------------------------
# 5. Main Pipeline Function
# ---------------------------------------------------

def compute_team_concentration_pipeline(
    seasons: list[int] | int,
    cache_dir: Optional[str] = None,
    use_cache: bool = False
) -> pd.DataFrame:
    """
    Complete pipeline to compute team concentration scores.
    
    Args:
        seasons: Season(s) to analyze
        cache_dir: Directory for caching data
        use_cache: Whether to use cached data if available
        
    Returns:
        DataFrame with team-week concentration scores
    """
    # Load data
    if use_cache and cache_dir:
        print("Loading data from cache...")
        data = load_cached_concentration_sources(cache_dir, seasons)
    else:
        print("Fetching fresh data from nflreadpy...")
        data = load_external_concentration_sources(seasons, cache_dir)
    
    # Build usage table
    print("Building weekly player usage table...")
    usage_df = build_weekly_player_usage(
        data['participation'],
        data['ff_opportunity']
    )
    
    # Compute concentration
    print("Computing team concentration scores...")
    concentration_df = compute_team_concentration(usage_df)
    
    # Add RAG indicators
    concentration_df['pass_conc_rag'] = concentration_df['pass_concentration_score'].apply(
        get_concentration_rag
    )
    concentration_df['pass_conc_label'] = concentration_df['pass_concentration_score'].apply(
        get_concentration_label
    )
    
    print(f"✅ Computed concentration for {len(concentration_df)} team-weeks")
    
    return concentration_df


# ---------------------------------------------------
# 6. Example Usage
# ---------------------------------------------------

if __name__ == "__main__":
    # Example: Compute concentration for 2024 season
    concentration = compute_team_concentration_pipeline(
        seasons=2024,
        cache_dir="./data/cache",
        use_cache=False
    )
    
    # Show sample results
    print("\nSample concentration scores:")
    print(concentration[
        ['season', 'week', 'team', 'pass_concentration_score', 
         'pass_conc_rag', 'pass_conc_label']
    ].head(10))
    
    # Save to CSV
    concentration.to_csv("./data/cache/team_concentration_2024.csv", index=False)
    print("\n✅ Saved concentration scores to CSV")
