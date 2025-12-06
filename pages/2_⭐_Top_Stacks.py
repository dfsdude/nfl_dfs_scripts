"""
Top Stacks & Boom/Bust Tool Page
Stack analysis with PROE integration and boom/bust modeling
Uses data/ loaders and components/ for visualization
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from utils.data_manager import DataManager

st.title("⭐ Top Stacks & Boom/Bust Tool")
st.caption("Player-level Boom/Bust model + matchup-aware stack explorer powered by ROO simulations")

# Show data status for this tool
DataManager.show_tool_data_status("Top Stacks")

# Check if required data is loaded
required_files = ['roo_projections', 'matchups', 'sharp_offense', 'sharp_defense', 'weekly_proe']

if DataManager.require_data(required_files, "Top Stacks"):
    
    import pandas as pd
    
    # Get data from global cache
    try:
        with st.spinner("📊 Loading data..."):
            roo_projections = DataManager.get_data('roo_projections')
            matchups = DataManager.get_data('matchups')
            sharp_offense = DataManager.get_data('sharp_offense')
            sharp_defense = DataManager.get_data('sharp_defense')
            weekly_proe = DataManager.get_data('weekly_proe')
        
        st.success(f"✅ Loaded: {len(roo_projections)} projections, {len(matchups)} matchups")
        
        # Import and run the core logic
        from modules import top_stacks
        top_stacks.run()
        
    except Exception as e:
        st.error(f"❌ **Error loading data**: {e}")
        st.info("💡 Make sure all CSV files have the correct format and column names")
