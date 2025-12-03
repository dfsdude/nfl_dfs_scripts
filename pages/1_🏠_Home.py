"""
Home page for DFS Tools Suite
Main landing page with tool descriptions and navigation
"""

import streamlit as st
from utils.config import init_app_config

# Initialize app configuration
init_app_config()

st.title("🏈 DFS Tools Suite")
st.markdown("### Welcome to the Unified DFS Analysis Platform")

st.markdown("""
This suite provides comprehensive tools for NFL DFS research, analysis, and lineup construction.
Use the sidebar to navigate between tools.
""")

# Tool descriptions
col1, col2 = st.columns(2)

with col1:
    st.markdown("### ⭐ Top Stacks & Boom/Bust Tool")
    st.markdown("""
    - **Purpose**: Identify optimal game stacks and boom/bust candidates
    - **Features**:
      - Game environment scoring with pace metrics
      - PROE integration for pass-heavy game scripts
      - Stack recommendations (QB + Bring-Back)
      - Boom/Bust ratings with ceiling/floor projections
      - Sharp Football metrics integration
    - **Use Case**: Pre-lineup construction research
    """)
    
    st.markdown("### 📊 Lineup Simulator")
    st.markdown("""
    - **Purpose**: Simulate your lineups against realistic field competition
    - **Features**:
      - Monte Carlo simulation (10k+ iterations)
      - Game correlation modeling
      - Field lineup generation with ownership
      - ROI calculation and cash probability
      - Top-finish probability analysis
    - **Use Case**: Post-lineup construction validation
    """)

with col2:
    st.markdown("### 🎲 Pre-Contest Simulator")
    st.markdown("""
    - **Purpose**: Optimize player pool and exposures before lock
    - **Features**:
      - ROO (Range of Outcomes) projections
      - Exposure optimization
      - Volatility analysis
      - Player pool recommendations
      - Risk/reward profiling
    - **Use Case**: Player pool selection and exposure planning
    """)
    
    st.markdown("### 🦃 Ownership Adjuster")
    st.markdown("""
    - **Purpose**: Normalize ownership projections to DK constraints
    - **Features**:
      - Position-based normalization
      - Roster construction compliance
      - Bulk ownership adjustments
      - CSV import/export
    - **Use Case**: Ownership projection calibration
    """)
    
    st.markdown("### 🏆 Contest Analyzer")
    st.markdown("""
    - **Purpose**: Post-contest analysis and learning
    - **Features**:
      - Ownership and leverage analysis
      - Stack construction review
      - Boom/bust accuracy tracking
      - ROI and profit calculation
      - Performance metrics
    - **Use Case**: Post-contest learning and process improvement
    """)

st.markdown("---")

st.markdown("### 🔧 Data Pipeline")
st.info("""
**Data Sources**:
- Sharp Football Analytics (EPA, Explosive Rate, PPD)
- Weekly PROE (Pass Rate Over Expected)
- Vegas Lines (Implied Totals, Spreads)
- Historical Player Stats (8-week lookback)
- DraftKings Salaries & Projections

**Output**: All tools work with standardized CSV files in `C:\\Users\\schne\\Documents\\DFS\\2025\\Dashboard\\`
""")

st.markdown("### 📈 Workflow Recommendation")
st.markdown("""
**Pre-Contest Workflow:**
1. **Pre-Contest Simulator** → Identify optimal player pool & exposures
2. **Top Stacks Tool** → Research game environments & stack opportunities  
3. **Generate Lineups** → Build lineups in your optimizer
4. **Lineup Simulator** → Validate lineups against field competition
5. **Ownership Adjuster** → Fine-tune ownership projections if needed

**Post-Contest Workflow:**
6. **Contest Analyzer** → Review results, identify leverage, learn from outcomes
""")

st.markdown("---")

st.markdown("### 🚀 Getting Started")
st.markdown("""
1. Ensure all data files are in the data directory
2. Run `python roo_simulator.py` to generate projections
3. Navigate to your desired tool using the sidebar
4. Upload any additional files as needed per tool
""")
