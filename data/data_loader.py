"""
Data loading module for DFS Tools Suite
Handles loading and caching of CSV data files
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from utils.config import DATA_DIR

# Try to import advanced stats loader
try:
    from data.load_advanced_stats import (
        load_all_advanced_stats,
        aggregate_recent_weeks,
        merge_with_dk_salaries,
        get_recent_advanced_stats
    )
    ADVANCED_STATS_AVAILABLE = True
except ImportError:
    ADVANCED_STATS_AVAILABLE = False

@st.cache_data(ttl=3600)
def load_weekly_stats() -> pd.DataFrame:
    """Load weekly player stats (8-week history)"""
    return pd.read_csv(DATA_DIR / "Weekly_Stats.csv")

@st.cache_data(ttl=3600)
def load_weekly_dst_stats() -> pd.DataFrame:
    """Load weekly DST stats"""
    return pd.read_csv(DATA_DIR / "Weekly_DST_Stats.csv")

@st.cache_data(ttl=3600)
def load_salaries() -> pd.DataFrame:
    """Load DraftKings salaries"""
    return pd.read_csv(DATA_DIR / "Salaries_2025.csv")

@st.cache_data(ttl=3600)
def load_matchups() -> pd.DataFrame:
    """
    Load matchup data (Vegas lines) from odds.csv
    Transforms odds.csv (home/away format) to Matchup.csv format (Init/Opp bidirectional)
    
    Returns DataFrame with columns:
    - Init: Initiating team (the team we're analyzing)
    - Opp: Opponent team
    - Spread: Point spread from Init team's perspective (negative = favored)
    - Total: Over/under line for the game
    - ITT: Implied Team Total = (Total / 2) + (Spread / 2)
    """
    # Try to load from odds-api first, fall back to legacy Matchup.csv
    odds_path = Path(__file__).parent.parent / "data" / "odds-api" / "odds.csv"
    
    if odds_path.exists():
        # Load odds data
        odds = pd.read_csv(odds_path)
        
        # Create two rows per game (home as Init, away as Init)
        matchup_rows = []
        
        for _, game in odds.iterrows():
            # Home team as Init
            home_row = {
                'Init': game['home_team'],
                'Opp': game['away_team'],
                'Spread': game['spread_home'],  # Already from home perspective
                'Total': game['over_under_line']
            }
            home_row['ITT'] = (home_row['Total'] / 2) + (home_row['Spread'] / 2)
            matchup_rows.append(home_row)
            
            # Away team as Init
            away_row = {
                'Init': game['away_team'],
                'Opp': game['home_team'],
                'Spread': -game['spread_home'],  # Flip spread for away team
                'Total': game['over_under_line']
            }
            away_row['ITT'] = (away_row['Total'] / 2) + (away_row['Spread'] / 2)
            matchup_rows.append(away_row)
        
        return pd.DataFrame(matchup_rows)
    else:
        # Fall back to legacy Matchup.csv
        return pd.read_csv(DATA_DIR / "Matchup.csv")

@st.cache_data(ttl=3600)
def load_sharp_offense() -> pd.DataFrame:
    """Load Sharp Football offensive metrics"""
    return pd.read_csv(DATA_DIR / "sharp_offense.csv")

@st.cache_data(ttl=3600)
def load_sharp_defense() -> pd.DataFrame:
    """Load Sharp Football defensive metrics"""
    return pd.read_csv(DATA_DIR / "sharp_defense.csv")

@st.cache_data(ttl=3600)
def load_weekly_proe() -> pd.DataFrame:
    """Load weekly PROE data"""
    return pd.read_csv(DATA_DIR / "weekly_proe_2025.csv")

@st.cache_data(ttl=3600)
def load_roo_projections() -> pd.DataFrame:
    """Load ROO simulator projections"""
    return pd.read_csv(DATA_DIR / "roo_projections.csv")

@st.cache_data(ttl=3600)
def load_player_mapping() -> pd.DataFrame:
    """Load player name mapping"""
    try:
        return pd.read_csv(DATA_DIR / "Player_Mapping.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=['Name', 'Mapped_Name'])

@st.cache_data(ttl=3600)
def load_projections() -> pd.DataFrame:
    """Load baseline projections"""
    try:
        return pd.read_csv(DATA_DIR / "projections_2025.csv")
    except FileNotFoundError:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_advanced_stats(lookback_weeks: int = 4) -> Optional[pd.DataFrame]:
    """
    Load FantasyPros advanced stats aggregated over recent weeks
    
    Args:
        lookback_weeks: Number of recent weeks to aggregate
    
    Returns:
        DataFrame with aggregated advanced stats or None if not available
    """
    if not ADVANCED_STATS_AVAILABLE:
        return None
    
    try:
        # Load and aggregate advanced stats
        stats = get_recent_advanced_stats(lookback_weeks=lookback_weeks)
        return stats
    except Exception as e:
        st.warning(f"Could not load advanced stats: {e}")
        return None

@st.cache_data(ttl=3600)
def load_advanced_stats_with_salaries(week: Optional[int] = None, lookback_weeks: int = 4) -> Optional[pd.DataFrame]:
    """
    Load FantasyPros advanced stats merged with DraftKings salaries
    
    Args:
        week: Week to load salaries for (None = current week)
        lookback_weeks: Number of weeks to aggregate stats
    
    Returns:
        Merged DataFrame or None if not available
    """
    if not ADVANCED_STATS_AVAILABLE:
        return None
    
    try:
        # Load salaries
        salaries = load_salaries()
        
        # Load and merge advanced stats
        stats = get_recent_advanced_stats(
            lookback_weeks=lookback_weeks,
            dk_salaries=salaries,
            current_week=week
        )
        return stats
    except Exception as e:
        st.warning(f"Could not load advanced stats with salaries: {e}")
        return None

def load_all_data() -> Dict[str, pd.DataFrame]:
    """
    Load all required data files
    Returns dictionary with all dataframes
    """
    return {
        'weekly_stats': load_weekly_stats(),
        'weekly_dst_stats': load_weekly_dst_stats(),
        'salaries': load_salaries(),
        'matchups': load_matchups(),
        'sharp_offense': load_sharp_offense(),
        'sharp_defense': load_sharp_defense(),
        'weekly_proe': load_weekly_proe(),
        'roo_projections': load_roo_projections(),
        'player_mapping': load_player_mapping(),
        'projections': load_projections()
    }

def save_dataframe(df: pd.DataFrame, filename: str) -> None:
    """Save dataframe to CSV in data directory"""
    filepath = DATA_DIR / filename
    df.to_csv(filepath, index=False)
    st.success(f"✓ Saved to {filepath}")
