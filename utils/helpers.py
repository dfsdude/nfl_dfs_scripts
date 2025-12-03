"""
Helper functions for DFS Tools Suite
Generic utility functions used across multiple tools
"""

def format_currency(value: float) -> str:
    """Format a number as currency"""
    return f"${value:,.2f}"

def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a decimal as percentage"""
    return f"{value * 100:.{decimals}f}%"

def calculate_leverage(actual_points: float, salary: int, ownership: float) -> float:
    """
    Calculate leverage score for a player
    Leverage = (Actual Points - Expected) / (Ownership + 1)
    """
    expected = salary / 1000  # Simple expectation: $1K = 1 point
    return (actual_points - expected) / (ownership + 1)

def normalize_player_name(name: str) -> str:
    """Normalize player names for matching"""
    return name.strip().replace("  ", " ").title()
