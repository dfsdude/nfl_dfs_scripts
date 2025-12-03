"""
Data loading module for DFS Tools Suite
Handles loading and caching of CSV data files
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from utils.config import DATA_DIR

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
    """Load matchup data (Vegas lines)"""
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
