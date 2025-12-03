"""
Pre-Contest Simulator Tool Page
Optimize player pool and exposures BEFORE lineup lock
Uses services/ for simulations and components/ for visualization
"""

import streamlit as st
from services.simulations import run_player_simulations, calculate_boom_probability
from components.charts import create_projection_distribution, create_floor_ceiling_chart
from utils.config import ROO_CONFIG

st.title("🎲 Pre-Contest Simulator")
st.caption("Optimize your player pool and exposures BEFORE lineup lock")

# Note about refactoring
st.info("""
✨ **Refactored to use modular architecture!**  
Now uses simulation services from `services/` and reusable visualization components.  
Legacy standalone version still available at `pre_contest_simulator.py`
""")

# Import and run the original tool logic
try:
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    # Import the modules directory version
    from modules import pre_contest_sim
    
    # Run the tool
    pre_contest_sim.run()
    
except Exception as e:
    st.error(f"Error loading tool: {e}")
    st.markdown("""
    **Workaround**: Run the standalone version:
    ```bash
    streamlit run pre_contest_simulator.py
    ```
    """)
