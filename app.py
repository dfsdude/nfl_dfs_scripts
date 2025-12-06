"""
Unified DFS Tools Suite - Main Application Launcher
Provides navigation to all DFS analysis tools from a single entry point.
Uses Streamlit's native multi-page app structure.
"""

import streamlit as st
from utils.config import init_app_config
from utils.data_manager import DataManager

# Initialize app configuration (must be first Streamlit command)
init_app_config()

# Sidebar branding
st.sidebar.title("🏈 DFS Tools Suite")
st.sidebar.markdown("---")

# Global data uploader (appears on all pages)
DataManager.show_global_uploader()

st.sidebar.markdown("### About")
st.sidebar.info(
    "Unified DFS analysis suite for NFL DraftKings contests. "
    "Built with Sharp Football metrics, PROE data, and Monte Carlo simulation."
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Version**: 2.0")
st.sidebar.markdown("**Last Updated**: December 2, 2025")

# Main page content - will be overridden by page navigation
st.title("🏈 DFS Tools Suite")
st.markdown("### Welcome!")
st.info("👈 Use the sidebar to navigate to different tools")

st.markdown("""
## Available Tools

Navigate using the sidebar to access:

- **🏠 Home** - Tool descriptions and workflow guide
- **⭐ Top Stacks** - Stack analysis with PROE integration  
- **📊 Lineup Simulator** - Monte Carlo lineup validation
- **🎲 Pre-Contest Simulator** - Exposure optimization
- **🦃 Ownership Adjuster** - Roster normalization
- **🏆 Contest Analyzer** - Post-contest analysis and learning
""")

st.markdown("---")
st.markdown("### Quick Start")
st.code("""
# 1. Generate ROO projections
python roo_simulator.py

# 2. Launch unified app
streamlit run app.py

# 3. Navigate using sidebar
""", language="bash")

