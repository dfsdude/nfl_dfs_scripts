"""
Top Stacks & Boom/Bust Tool Page
Stack analysis with PROE integration and boom/bust modeling
Uses data/ loaders and components/ for visualization
"""

import streamlit as st
from data.data_loader import (
    load_roo_projections, load_matchups, load_sharp_offense, 
    load_sharp_defense, load_weekly_proe
)
from utils.constants import TEAM_MAPPING

st.title("⭐ Top Stacks & Boom/Bust Tool")
st.caption("Player-level Boom/Bust model + matchup-aware stack explorer powered by ROO simulations")

# Load data using modular loaders
try:
    with st.spinner("📊 Loading data from centralized loaders..."):
        roo_projections = load_roo_projections()
        matchups = load_matchups()
        sharp_offense = load_sharp_offense()
        sharp_defense = load_sharp_defense()
        weekly_proe = load_weekly_proe()
        
    st.success(f"✅ Loaded: {len(roo_projections)} projections, {len(matchups)} matchups")
    
    # Import and run the core logic (temporarily using modules until full refactor)
    import sys
    from pathlib import Path
    
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    from modules import top_stacks
    top_stacks.run()
    
except FileNotFoundError as e:
    st.error(f"❌ **Data File Not Found**: {e}")
    st.info("💡 Check that all required CSV files are in the Dashboard directory")
except Exception as e:
    st.error(f"❌ **Error**: {e}")
    st.markdown("""
    **Workaround**: Run the standalone version:
    ```bash
    streamlit run top_stacks_tool.py
    ```
    """)
