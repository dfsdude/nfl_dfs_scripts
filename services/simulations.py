"""
Monte Carlo simulation services
Pure business logic without Streamlit dependencies
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict

def run_player_simulations(
    mean: float,
    std: float,
    n_simulations: int = 10000
) -> np.ndarray:
    """
    Run Monte Carlo simulations for a single player
    
    Args:
        mean: Expected points
        std: Standard deviation
        n_simulations: Number of simulations to run
        
    Returns:
        Array of simulated point values
    """
    return np.random.normal(mean, std, n_simulations)

def run_lognormal_simulations(
    mu_log: float,
    sigma_log: float,
    n_simulations: int = 10000
) -> np.ndarray:
    """
    Run Monte Carlo simulations using lognormal distribution
    
    Args:
        mu_log: Mean of underlying normal distribution
        sigma_log: Standard deviation of underlying normal
        n_simulations: Number of simulations
        
    Returns:
        Array of simulated point values
    """
    return np.random.lognormal(mu_log, sigma_log, n_simulations)

def calculate_percentiles(
    simulations: np.ndarray,
    percentiles: list = [15, 50, 85]
) -> Dict[str, float]:
    """
    Calculate percentiles from simulation results
    
    Args:
        simulations: Array of simulated values
        percentiles: List of percentiles to calculate
        
    Returns:
        Dictionary with percentile values
    """
    results = {}
    for p in percentiles:
        results[f"p{p}"] = np.percentile(simulations, p)
    return results

def calculate_boom_probability(
    simulations: np.ndarray,
    salary: int,
    boom_multiplier: float = 4.0
) -> float:
    """
    Calculate probability of hitting boom threshold (4x salary)
    
    Args:
        simulations: Array of simulated point values
        salary: Player salary
        boom_multiplier: Multiplier for boom threshold (default 4.0)
        
    Returns:
        Probability between 0 and 1
    """
    boom_threshold = (salary / 1000) * boom_multiplier
    return np.mean(simulations >= boom_threshold)

def simulate_correlated_players(
    means: np.ndarray,
    stds: np.ndarray,
    correlation_matrix: np.ndarray,
    n_simulations: int = 10000
) -> np.ndarray:
    """
    Simulate multiple correlated players
    
    Args:
        means: Array of player means
        stds: Array of player standard deviations
        correlation_matrix: Correlation matrix between players
        n_simulations: Number of simulations
        
    Returns:
        2D array of shape (n_simulations, n_players)
    """
    n_players = len(means)
    
    # Create covariance matrix from correlation matrix and stds
    cov_matrix = np.outer(stds, stds) * correlation_matrix
    
    # Generate correlated random numbers
    random_values = np.random.multivariate_normal(
        mean=np.zeros(n_players),
        cov=correlation_matrix,
        size=n_simulations
    )
    
    # Scale to desired means and stds
    simulations = means + (random_values * stds)
    
    return simulations

def calculate_lineup_score(player_simulations: np.ndarray, indices: list) -> float:
    """
    Calculate total lineup score from individual player simulations
    
    Args:
        player_simulations: 2D array of player simulations
        indices: List of player indices to include in lineup
        
    Returns:
        Total lineup score
    """
    return player_simulations[:, indices].sum(axis=1)
