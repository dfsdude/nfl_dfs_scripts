"""
Reusable layout components for DFS Tools Suite
"""

import streamlit as st

def create_metric_card(title: str, value: str, delta: str = None, help_text: str = None):
    """
    Create a metric display card
    
    Args:
        title: Metric title
        value: Metric value (formatted string)
        delta: Optional delta/change value
        help_text: Optional help tooltip
    """
    st.metric(label=title, value=value, delta=delta, help=help_text)

def create_three_column_metrics(metrics: list):
    """
    Create three metrics in a row
    
    Args:
        metrics: List of dicts with keys: title, value, delta, help
    """
    cols = st.columns(3)
    for i, metric in enumerate(metrics[:3]):
        with cols[i]:
            create_metric_card(
                title=metric['title'],
                value=metric['value'],
                delta=metric.get('delta'),
                help_text=metric.get('help')
            )

def create_info_box(title: str, content: str, type: str = "info"):
    """
    Create an information box
    
    Args:
        title: Box title
        content: Box content
        type: Box type (info, success, warning, error)
    """
    box_func = {
        'info': st.info,
        'success': st.success,
        'warning': st.warning,
        'error': st.error
    }.get(type, st.info)
    
    box_func(f"**{title}**\n\n{content}")

def create_expander_section(title: str, content_func, expanded: bool = False):
    """
    Create collapsible expander section
    
    Args:
        title: Expander title
        content_func: Function to call to render content
        expanded: Whether to start expanded
    """
    with st.expander(title, expanded=expanded):
        content_func()

def create_sidebar_filters(filter_configs: list):
    """
    Create sidebar filter widgets
    
    Args:
        filter_configs: List of dicts with filter configurations
            Each dict should have: type, label, options, default, key
    
    Returns:
        Dict of filter values
    """
    filters = {}
    
    with st.sidebar:
        st.title("⚙️ Filters")
        
        for config in filter_configs:
            filter_type = config['type']
            
            if filter_type == 'multiselect':
                filters[config['key']] = st.multiselect(
                    config['label'],
                    options=config['options'],
                    default=config.get('default', [])
                )
            elif filter_type == 'selectbox':
                filters[config['key']] = st.selectbox(
                    config['label'],
                    options=config['options'],
                    index=config.get('default', 0)
                )
            elif filter_type == 'slider':
                filters[config['key']] = st.slider(
                    config['label'],
                    min_value=config['min'],
                    max_value=config['max'],
                    value=config.get('default', config['min'])
                )
            elif filter_type == 'number_input':
                filters[config['key']] = st.number_input(
                    config['label'],
                    min_value=config.get('min', 0),
                    max_value=config.get('max', 1000),
                    value=config.get('default', 0)
                )
    
    return filters

def create_two_column_layout():
    """Create two-column layout and return column objects"""
    return st.columns(2)

def create_tabs(tab_names: list):
    """
    Create tabs and return tab objects
    
    Args:
        tab_names: List of tab names
        
    Returns:
        Tuple of tab objects
    """
    return st.tabs(tab_names)
