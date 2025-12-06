"""
Reusable table components for DFS Tools Suite
"""

import streamlit as st
import pandas as pd

def display_player_table(
    df: pd.DataFrame,
    columns: list = None,
    title: str = None,
    width: str = 'stretch'
) -> None:
    """
    Display formatted player table with optional title
    
    Args:
        df: DataFrame to display
        columns: List of columns to show (None = all columns)
        title: Optional table title
        width: Width mode - 'stretch' for full container width, 'content' for auto
    """
    if title:
        st.subheader(title)
    
    display_df = df[columns] if columns else df
    st.dataframe(display_df, width=width)

def display_styled_table(
    df: pd.DataFrame,
    highlight_columns: dict = None,
    title: str = None
) -> None:
    """
    Display table with conditional formatting
    
    Args:
        df: DataFrame to display
        highlight_columns: Dict mapping column names to styling rules
        title: Optional table title
    """
    if title:
        st.subheader(title)
    
    styled_df = df.style
    
    if highlight_columns:
        for col, style_config in highlight_columns.items():
            if style_config['type'] == 'background_gradient':
                styled_df = styled_df.background_gradient(
                    subset=[col],
                    cmap=style_config.get('cmap', 'RdYlGn'),
                    vmin=style_config.get('vmin'),
                    vmax=style_config.get('vmax')
                )
            elif style_config['type'] == 'bar':
                styled_df = styled_df.bar(
                    subset=[col],
                    color=style_config.get('color', 'lightblue')
                )
    
    st.dataframe(styled_df, width='stretch')

def create_comparison_table(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    label1: str = "Your Lineup",
    label2: str = "Field Average",
    metric_col: str = "Ownership"
) -> pd.DataFrame:
    """
    Create side-by-side comparison table
    
    Args:
        df1: First dataframe
        df2: Second dataframe
        label1: Label for first dataset
        label2: Label for second dataset
        metric_col: Column to compare
        
    Returns:
        Merged comparison dataframe
    """
    comparison = df1[['Player', metric_col]].merge(
        df2[['Player', metric_col]],
        on='Player',
        how='outer',
        suffixes=(f' ({label1})', f' ({label2})')
    )
    
    # Calculate difference
    comparison['Difference'] = (
        comparison[f'{metric_col} ({label1})'] - 
        comparison[f'{metric_col} ({label2})']
    )
    
    return comparison.sort_values('Difference', ascending=False)

def display_download_button(
    df: pd.DataFrame,
    filename: str = "data.csv",
    button_label: str = "📥 Download CSV"
) -> None:
    """
    Display download button for dataframe
    
    Args:
        df: DataFrame to download
        filename: Output filename
        button_label: Button text
    """
    csv = df.to_csv(index=False)
    st.download_button(
        label=button_label,
        data=csv,
        file_name=filename,
        mime="text/csv"
    )
