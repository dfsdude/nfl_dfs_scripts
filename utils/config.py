"""
Configuration module for DFS Tools Suite
Handles app-wide configuration and setup
"""

import streamlit as st
from pathlib import Path

# Data directory path
DATA_DIR = Path(r"C:\Users\schne\Documents\DFS\2025\Dashboard")

# App configuration
APP_CONFIG = {
    "title": "DFS Tools Suite",
    "icon": "🏈",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# ROO Simulator configuration
ROO_CONFIG = {
    "n_simulations": 10000,
    "lookback_weeks": 8,
    "min_games_for_player": 4,
    "floor_percentile": 15,
    "ceiling_percentile": 85,
    "matchup_vol_min": 0.8,
    "matchup_vol_max": 1.3,
    "min_std": 3.0,
    "max_std": 25.0,
    "min_sigma_log": 0.1,
    "max_sigma_log": 1.0
}

# Position defaults for volatility
POSITION_DEFAULTS = {
    "QB": 5.5,
    "RB": 5.0,
    "WR": 5.0,
    "TE": 4.5,
    "DST": 3.0
}

def init_app_config():
    """Initialize Streamlit page configuration"""
    st.set_page_config(
        page_title=APP_CONFIG["title"],
        page_icon=APP_CONFIG["icon"],
        layout=APP_CONFIG["layout"],
        initial_sidebar_state=APP_CONFIG["initial_sidebar_state"]
    )

def get_data_path(filename: str) -> Path:
    """Get full path to a data file"""
    return DATA_DIR / filename
