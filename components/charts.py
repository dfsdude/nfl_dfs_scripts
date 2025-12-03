"""
Reusable chart components for DFS Tools Suite
Uses Plotly for interactive visualizations
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.constants import POSITION_COLORS

def create_ownership_scatter(
    df: pd.DataFrame,
    x_col: str = "Own%",
    y_col: str = "FPTS",
    color_col: str = "Position",
    hover_data: list = None
) -> go.Figure:
    """Create ownership vs performance scatter plot"""
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        hover_data=hover_data or ['Player', 'Salary'],
        color_discrete_map=POSITION_COLORS,
        title="Ownership vs Performance"
    )
    fig.update_layout(
        xaxis_title="Ownership %",
        yaxis_title="Fantasy Points",
        hovermode='closest'
    )
    return fig

def create_volatility_bar_chart(
    df: pd.DataFrame,
    player_col: str = "Player",
    volatility_col: str = "Volatility_Index"
) -> go.Figure:
    """Create bar chart of player volatility"""
    fig = px.bar(
        df.sort_values(volatility_col, ascending=False).head(20),
        x=player_col,
        y=volatility_col,
        title="Top 20 Most Volatile Players",
        color=volatility_col,
        color_continuous_scale="Reds"
    )
    fig.update_layout(
        xaxis_title="Player",
        yaxis_title="Volatility Index",
        xaxis={'categoryorder': 'total descending'}
    )
    return fig

def create_projection_distribution(
    simulations: list,
    player_name: str
) -> go.Figure:
    """Create histogram of simulation results"""
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=simulations,
        nbinsx=50,
        name=player_name,
        marker_color='lightblue'
    ))
    fig.update_layout(
        title=f"Projection Distribution: {player_name}",
        xaxis_title="Fantasy Points",
        yaxis_title="Frequency",
        showlegend=False
    )
    return fig

def create_floor_ceiling_chart(
    df: pd.DataFrame,
    player_col: str = "Player",
    floor_col: str = "Floor_Proj",
    ceiling_col: str = "Ceiling_Proj",
    median_col: str = "OWS_Median_Proj"
) -> go.Figure:
    """Create chart showing floor/median/ceiling for top players"""
    df_top = df.nlargest(15, median_col)
    
    fig = go.Figure()
    
    # Add floor line
    fig.add_trace(go.Scatter(
        x=df_top[player_col],
        y=df_top[floor_col],
        mode='markers+lines',
        name='Floor (15th %ile)',
        line=dict(color='red', dash='dash'),
        marker=dict(size=8)
    ))
    
    # Add median line
    fig.add_trace(go.Scatter(
        x=df_top[player_col],
        y=df_top[median_col],
        mode='markers+lines',
        name='Median (50th %ile)',
        line=dict(color='blue'),
        marker=dict(size=10)
    ))
    
    # Add ceiling line
    fig.add_trace(go.Scatter(
        x=df_top[player_col],
        y=df_top[ceiling_col],
        mode='markers+lines',
        name='Ceiling (85th %ile)',
        line=dict(color='green', dash='dash'),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Floor / Median / Ceiling Projections",
        xaxis_title="Player",
        yaxis_title="Projected Points",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_position_distribution(
    df: pd.DataFrame,
    position_col: str = "Position"
) -> go.Figure:
    """Create pie chart of position distribution"""
    position_counts = df[position_col].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=position_counts.index,
        values=position_counts.values,
        marker=dict(colors=[POSITION_COLORS.get(pos, '#999') for pos in position_counts.index])
    )])
    
    fig.update_layout(title="Position Distribution")
    
    return fig
