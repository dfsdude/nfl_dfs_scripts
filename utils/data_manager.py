"""
Global Data Manager for DFS Tools Suite
Centralized file upload and caching across all tools
"""

import streamlit as st
import pandas as pd
from typing import Dict, Optional

class DataManager:
    """Manages shared data files across all tools using st.session_state"""
    
    # Common file types used across tools
    FILE_TYPES = {
        'roo_projections': {
            'name': 'ROO Projections',
            'help': 'Range of Outcomes projections with floor/ceiling/median',
            'required_by': ['Top Stacks', 'Contest Analyzer']
        },
        'matchups': {
            'name': 'Matchups',
            'help': 'Game matchups with implied totals and spreads',
            'required_by': ['Top Stacks', 'Pre-Contest Simulator', 'Lineup Simulator']
        },
        'sharp_offense': {
            'name': 'Sharp Offense',
            'help': 'Sharp Football offensive metrics (EPA, explosive rate, PPD)',
            'required_by': ['Top Stacks', 'Pre-Contest Simulator']
        },
        'sharp_defense': {
            'name': 'Sharp Defense',
            'help': 'Sharp Football defensive metrics (EPA allowed, explosive rate allowed)',
            'required_by': ['Top Stacks', 'Pre-Contest Simulator']
        },
        'weekly_proe': {
            'name': 'Weekly PROE',
            'help': 'Pass Rate Over Expected by team and week',
            'required_by': ['Top Stacks']
        },
        'contest_results': {
            'name': 'Contest Results',
            'help': 'Contest entries with actual scores',
            'required_by': ['Contest Analyzer']
        },
        'lineups': {
            'name': 'Lineups',
            'help': 'DraftKings lineup export',
            'required_by': ['Lineup Simulator']
        },
        'salaries': {
            'name': 'Salaries',
            'help': 'DraftKings salary file',
            'required_by': ['Lineup Simulator']
        }
    }
    
    @staticmethod
    def initialize():
        """Initialize session state for data management"""
        if 'data_cache' not in st.session_state:
            st.session_state.data_cache = {}
        if 'file_uploads' not in st.session_state:
            st.session_state.file_uploads = {}
    
    @staticmethod
    def show_global_uploader():
        """Display global file uploader in sidebar"""
        DataManager.initialize()
        
        st.sidebar.markdown("---")
        st.sidebar.header("📁 Global Data Files")
        st.sidebar.caption("Upload once, use across all tools")
        
        with st.sidebar.expander("📤 Upload Data Files", expanded=False):
            for key, config in DataManager.FILE_TYPES.items():
                file = st.file_uploader(
                    config['name'],
                    type=['csv'],
                    help=config['help'],
                    key=f"global_{key}"
                )
                
                if file is not None:
                    # Store uploaded file
                    st.session_state.file_uploads[key] = file
                    
                    # Load and cache data
                    try:
                        if key not in st.session_state.data_cache:
                            df = pd.read_csv(file)
                            st.session_state.data_cache[key] = df
                            st.sidebar.success(f"✅ {config['name']}: {len(df)} rows")
                    except Exception as e:
                        st.sidebar.error(f"❌ Error loading {config['name']}: {str(e)}")
            
            # Show what's currently loaded
            if st.session_state.data_cache:
                st.sidebar.markdown("### 📦 Loaded Data")
                for key, df in st.session_state.data_cache.items():
                    config = DataManager.FILE_TYPES.get(key, {})
                    st.sidebar.text(f"✓ {config.get('name', key)}: {len(df)} rows")
                
                if st.sidebar.button("🗑️ Clear All Data"):
                    st.session_state.data_cache = {}
                    st.session_state.file_uploads = {}
                    st.rerun()
    
    @staticmethod
    def get_data(data_key: str) -> Optional[pd.DataFrame]:
        """
        Get cached data by key
        
        Args:
            data_key: Key from FILE_TYPES
            
        Returns:
            DataFrame if loaded, None otherwise
        """
        DataManager.initialize()
        return st.session_state.data_cache.get(data_key)
    
    @staticmethod
    def get_file(file_key: str):
        """
        Get uploaded file object by key
        
        Args:
            file_key: Key from FILE_TYPES
            
        Returns:
            File object if uploaded, None otherwise
        """
        DataManager.initialize()
        return st.session_state.file_uploads.get(file_key)
    
    @staticmethod
    def is_loaded(data_key: str) -> bool:
        """Check if data is loaded"""
        DataManager.initialize()
        return data_key in st.session_state.data_cache
    
    @staticmethod
    def get_required_files(tool_name: str) -> Dict[str, dict]:
        """
        Get list of required files for a specific tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dict of file configs required by this tool
        """
        required = {}
        for key, config in DataManager.FILE_TYPES.items():
            if tool_name in config.get('required_by', []):
                required[key] = config
        return required
    
    @staticmethod
    def show_tool_data_status(tool_name: str, required_files: list = None):
        """
        Show data status for current tool
        
        Args:
            tool_name: Name of the current tool
            required_files: List of required file keys (optional)
        """
        DataManager.initialize()
        
        if required_files is None:
            # Auto-detect from FILE_TYPES
            required_files = [
                key for key, config in DataManager.FILE_TYPES.items()
                if tool_name in config.get('required_by', [])
            ]
        
        if not required_files:
            return
        
        loaded = [key for key in required_files if DataManager.is_loaded(key)]
        missing = [key for key in required_files if not DataManager.is_loaded(key)]
        
        if loaded:
            st.sidebar.success(f"✅ {len(loaded)}/{len(required_files)} files loaded")
        
        if missing:
            st.sidebar.warning(
                f"⚠️ Missing {len(missing)} file(s):\n" + 
                "\n".join([f"- {DataManager.FILE_TYPES[key]['name']}" for key in missing])
            )
            st.sidebar.info("👆 Upload in 'Global Data Files' section above")
    
    @staticmethod
    def require_data(data_keys: list, tool_name: str = "This tool") -> bool:
        """
        Check if required data is loaded, show error if not
        
        Args:
            data_keys: List of required data keys
            tool_name: Name of tool for error message
            
        Returns:
            True if all data loaded, False otherwise
        """
        DataManager.initialize()
        
        missing = [key for key in data_keys if not DataManager.is_loaded(key)]
        
        if missing:
            st.error(
                f"❌ **{tool_name} requires the following data files:**\n\n" +
                "\n".join([
                    f"- **{DataManager.FILE_TYPES[key]['name']}**: {DataManager.FILE_TYPES[key]['help']}"
                    for key in missing
                ])
            )
            st.info("👆 Upload files in the sidebar under 'Global Data Files'")
            return False
        
        return True
