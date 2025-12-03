"""
Lineup Simulator Tool Page
Comprehensive DFS lineup simulation with game environment modeling
Uses services/ for simulations and components/ for visualization
"""

import streamlit as st
from services.simulations import run_player_simulations, calculate_boom_probability
from utils.config import ROO_CONFIG

st.title("📊 DFS Lineup Simulator")
st.caption("Simulate entire slate with game environment modeling and field competition")

# Import and run the original tool logic
try:
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    # Import the modules directory version
    from modules import sims_tool
    
    # Run the tool
    sims_tool.run()
    
except Exception as e:
    st.error(f"Error loading tool: {e}")
    st.markdown("""
    **Workaround**: Run the standalone version:
    ```bash
    streamlit run sims_tool.py
    ```
    """)
