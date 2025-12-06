"""
NFL DFS Range-of-Outcomes (ROO) Simulation Engine

Generates floor, median, and ceiling fantasy point projections via Monte Carlo simulation.
Uses historical volatility + OWS median projections + matchup adjustments.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

class ROOConfig:
    """Configuration for ROO simulation"""
    
    # Data directory
    DATA_DIR = os.environ.get("DFS_DATA_DIR", r"C:\Users\schne\Documents\DFS\2025\Dashboard")
    
    # Simulation parameters
    N_SIMULATIONS = 10000  # Number of Monte Carlo iterations
    RANDOM_SEED = 42  # For reproducibility
    
    # Historical data lookback
    MIN_GAMES_FOR_PLAYER = 4  # Minimum games to use player-specific volatility
    LOOKBACK_WEEKS = 8  # How many recent weeks to analyze
    
    # Volatility constraints
    MIN_STD = 3.0  # Minimum standard deviation (floor for volatility)
    MAX_STD = 20.0  # Maximum standard deviation (cap for extreme volatility)
    
    # Lognormal distribution constraints
    MIN_SIGMA_LOG = 0.2  # Minimum sigma for lognormal
    MAX_SIGMA_LOG = 1.5  # Maximum sigma for lognormal
    
    # Percentiles to calculate
    PERCENTILES = [10, 15, 25, 50, 75, 85, 90, 95]
    FLOOR_PERCENTILE = 15  # P15
    CEILING_PERCENTILE = 85  # P85
    
    # Matchup adjustment bounds
    MATCHUP_VOL_MIN = 0.8  # Minimum matchup volatility multiplier (tough matchup)
    MATCHUP_VOL_MAX = 1.3  # Maximum matchup volatility multiplier (soft matchup)
    
    # Small epsilon for numerical stability
    EPS = 0.1


# ============================================================================
# DATA LOADING
# ============================================================================

def load_data() -> Dict[str, pd.DataFrame]:
    """Load all required data files"""
    
    data_dir = Path(ROOConfig.DATA_DIR)
    
    print("Loading data files...")
    
    # Load all files
    data = {
        'weekly_stats': pd.read_csv(data_dir / "Weekly_Stats.csv"),
        'weekly_dst_stats': pd.read_csv(data_dir / "Weekly_DST_Stats.csv"),
        'matchups': pd.read_csv(data_dir / "Matchup.csv"),
        'sharp_offense': pd.read_csv(data_dir / "sharp_offense.csv"),
        'sharp_defense': pd.read_csv(data_dir / "sharp_defense.csv"),
        'salaries': pd.read_csv(data_dir / "Salaries_2025.csv"),
        'projections': pd.read_csv(data_dir / "ows_projections.csv"),
        'player_mapping': pd.read_csv(data_dir / "Player_Mapping.csv"),
        'weekly_proe': pd.read_csv(data_dir / "weekly_proe_2025.csv"),
    }
    
    print(f"✓ Loaded {len(data['weekly_stats'])} historical player-game records")
    print(f"✓ Loaded {len(data['weekly_dst_stats'])} historical DST-game records")
    print(f"✓ Loaded {len(data['projections'])} current week projections")
    print(f"✓ Loaded {len(data['weekly_proe'])} PROE records")
    print(f"✓ Loaded {len(data['player_mapping'])} player name mappings")
    
    return data


# ============================================================================
# HISTORICAL VOLATILITY CALCULATION
# ============================================================================

def build_player_volatility(weekly_stats: pd.DataFrame, weekly_dst_stats: pd.DataFrame, player_mapping: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate historical volatility metrics for each player (including DST).
    
    Args:
        weekly_stats: Historical player stats
        weekly_dst_stats: Historical DST stats
        player_mapping: Name mapping across data sources
    
    Returns DataFrame with:
    - Player, Team, Position
    - hist_games (count of games)
    - hist_mean_fpts (average fantasy points)
    - hist_std_fpts (standard deviation)
    - effective_std_fpts (after fallback to position avg if low sample)
    """
    
    print("\nCalculating historical volatility...")
    
    # Create mapping dictionary: Weekly_Stats name -> standardized name (use DK_Salaries as standard)
    name_map = dict(zip(player_mapping['Weekly_Stats'], player_mapping['DK_Salaries']))
    mapped_count = len(name_map)
    print(f"  Loaded {mapped_count} name mappings from Player_Mapping.csv")
    
    # Process offensive players
    max_week = weekly_stats['Week'].max()
    lookback_cutoff = max_week - ROOConfig.LOOKBACK_WEEKS
    recent_stats = weekly_stats[weekly_stats['Week'] > lookback_cutoff].copy()
    
    # Standardize player names
    recent_stats['Player'] = recent_stats['Player'].map(name_map).fillna(recent_stats['Player'])
    
    unmapped_players = recent_stats[~recent_stats['Player'].isin(name_map.values())]['Player'].nunique()
    print(f"  {unmapped_players} unique players in Weekly_Stats not in mapping (using original names)")
    
    print(f"  Using weeks {lookback_cutoff + 1} to {max_week} ({ROOConfig.LOOKBACK_WEEKS} weeks)")
    
    # Player-level aggregation
    player_agg = recent_stats.groupby(['Player', 'Team', 'Position']).agg({
        'DK_Points': ['count', 'mean', 'std', 'min', 'max']
    }).reset_index()
    
    # Flatten multi-level columns
    player_agg.columns = ['Player', 'Team', 'Position', 'hist_games', 
                          'hist_mean_fpts', 'hist_std_fpts', 'hist_min_fpts', 'hist_max_fpts']
    
    print(f"  Aggregated stats for {len(player_agg)} unique players from Weekly_Stats")
    print(f"    Sample players: {player_agg['Player'].head(5).tolist()}")
    
    # Process DST (defense/special teams)
    dst_max_week = weekly_dst_stats['Week'].max()
    dst_lookback = dst_max_week - ROOConfig.LOOKBACK_WEEKS
    recent_dst = weekly_dst_stats[weekly_dst_stats['Week'] > dst_lookback].copy()
    
    # Standardize DST names using mapping
    recent_dst['Player'] = recent_dst['Player'].map(name_map).fillna(recent_dst['Player'])
    
    # DST aggregation (Player column is team name, e.g., "49ers")
    dst_agg = recent_dst.groupby(['Player', 'Team']).agg({
        'DK_Points': ['count', 'mean', 'std', 'min', 'max']
    }).reset_index()
    
    dst_agg.columns = ['Player', 'Team', 'hist_games', 
                       'hist_mean_fpts', 'hist_std_fpts', 'hist_min_fpts', 'hist_max_fpts']
    dst_agg['Position'] = 'DST'
    
    # Combine offensive players and DST
    all_players = pd.concat([player_agg, dst_agg], ignore_index=True)
    
    # Fill NaN std (happens when only 1 game) with mean * 0.5
    all_players['hist_std_fpts'] = all_players['hist_std_fpts'].fillna(
        all_players['hist_mean_fpts'] * 0.5
    )
    
    # Position-level aggregation (for players with low sample)
    position_agg = pd.concat([
        recent_stats.groupby('Position').agg({'DK_Points': ['mean', 'std']}).reset_index(),
        recent_dst.assign(Position='DST').groupby('Position').agg({'DK_Points': ['mean', 'std']}).reset_index()
    ], ignore_index=True)
    position_agg.columns = ['Position', 'pos_mean_fpts', 'pos_std_fpts']
    
    # Merge position averages
    all_players = all_players.merge(position_agg, on='Position', how='left')
    
    # Calculate effective std with fallback logic
    # If < MIN_GAMES: blend player std with position std
    def calc_effective_std(row):
        if row['hist_games'] >= ROOConfig.MIN_GAMES_FOR_PLAYER:
            return row['hist_std_fpts']
        elif row['hist_games'] >= 2:
            # Blend: weight toward position avg
            weight_player = row['hist_games'] / ROOConfig.MIN_GAMES_FOR_PLAYER
            weight_pos = 1 - weight_player
            return (weight_player * row['hist_std_fpts'] + 
                   weight_pos * row['pos_std_fpts'])
        else:
            # Very low sample: use position std with 20% boost (uncertainty premium)
            return row['pos_std_fpts'] * 1.2
    
    all_players['effective_std_fpts'] = all_players.apply(calc_effective_std, axis=1)
    
    # Calculate coefficient of variation
    all_players['hist_cv'] = all_players['hist_std_fpts'] / (all_players['hist_mean_fpts'] + 0.01)
    
    print(f"✓ Calculated volatility for {len(all_players)} players (including DST)")
    print(f"  Players with {ROOConfig.MIN_GAMES_FOR_PLAYER}+ games: "
          f"{(all_players['hist_games'] >= ROOConfig.MIN_GAMES_FOR_PLAYER).sum()}")
    print(f"  DST units: {(all_players['Position'] == 'DST').sum()}")
    
    return all_players[['Player', 'Team', 'Position', 'hist_games', 'hist_mean_fpts', 
                       'hist_std_fpts', 'effective_std_fpts', 'hist_cv', 
                       'hist_min_fpts', 'hist_max_fpts']]


# ============================================================================
# MATCHUP ADJUSTMENT
# ============================================================================

def compute_league_averages(sharp_offense: pd.DataFrame, 
                           sharp_defense: pd.DataFrame,
                           matchups: pd.DataFrame) -> dict:
    """
    Calculate league averages for normalization.
    
    Returns dictionary with league average metrics.
    """
    
    league_avgs = {
        # Offensive metrics
        'EPA_Play': sharp_offense['EPA_Play'].mean(),
        'Explosive_Play_Rate': sharp_offense['Explosive Play Rate'].mean(),
        'Points_Per_Drive': sharp_offense['Points Per Drive'].mean(),
        
        # Defensive metrics
        'EPA_Play_Allowed': sharp_defense['EPA_Play_Allowed'].mean(),
        'Explosive_Play_Rate_Allowed': sharp_defense['Explosive Play Rate Allowed'].mean(),
        'Points_Per_Drive_Allowed': sharp_defense['Points Per Drive Allowed'].mean(),
        
        # Implied total (from matchups)
        'Implied_Total': matchups['ITT'].mean() if 'ITT' in matchups.columns else 24.0
    }
    
    return league_avgs


def calculate_weighted_proe(team_abbrev: str, weekly_proe: pd.DataFrame, 
                           lookback_weeks: int = 8) -> float:
    """
    Calculate time-weighted PROE for a team, favoring recent weeks.
    
    Uses exponential decay: most recent week gets weight 1.0, 
    prior weeks decay by 0.85 per week.
    
    Args:
        team_abbrev: Team abbreviation (e.g., 'BUF', 'KC')
        weekly_proe: DataFrame with columns [season, week, posteam, proe]
        lookback_weeks: Number of weeks to include (default 8)
    
    Returns:
        Weighted PROE value (positive = pass-heavy, negative = run-heavy)
    """
    abbrev_to_full = {
        'ARI': 'Cardinals', 'ATL': 'Falcons', 'BAL': 'Ravens', 'BUF': 'Bills',
        'CAR': 'Panthers', 'CHI': 'Bears', 'CIN': 'Bengals', 'CLE': 'Browns',
        'DAL': 'Cowboys', 'DEN': 'Broncos', 'DET': 'Lions', 'GB': 'Packers',
        'HOU': 'Texans', 'IND': 'Colts', 'JAX': 'Jaguars', 'KC': 'Chiefs',
        'LAC': 'Chargers', 'LAR': 'Rams', 'LV': 'Raiders', 'MIA': 'Dolphins',
        'MIN': 'Vikings', 'NE': 'Patriots', 'NO': 'Saints', 'NYG': 'Giants',
        'NYJ': 'Jets', 'PHI': 'Eagles', 'PIT': 'Steelers', 'SEA': 'Seahawks',
        'SF': '49ers', 'TB': 'Buccaneers', 'TEN': 'Titans', 'WAS': 'Commanders'
    }
    
    # Convert abbreviation to full name for matching
    team_full = abbrev_to_full.get(team_abbrev, team_abbrev)
    
    # Filter to this team's recent weeks
    team_proe = weekly_proe[weekly_proe['posteam'] == team_full].copy()
    
    if team_proe.empty:
        return 0.0
    
    # Sort by week descending (most recent first)
    team_proe = team_proe.sort_values('week', ascending=False).head(lookback_weeks)
    
    # Apply exponential decay weights: 1.0, 0.85, 0.72, 0.61, 0.52, ...
    weights = [0.85 ** i for i in range(len(team_proe))]
    total_weight = sum(weights)
    
    if total_weight == 0:
        return 0.0
    
    # Calculate weighted average
    weighted_proe = sum(row['proe'] * weight 
                       for row, weight in zip(team_proe.to_dict('records'), weights))
    
    return weighted_proe / total_weight


def compute_matchup_multiplier(row: pd.Series, league_avgs: dict, weekly_proe: pd.DataFrame = None) -> float:
    """
    Calculate matchup-based volatility multiplier using Sharp Football metrics and PROE.
    
    Combines:
    - Team offensive quality (EPA, Explosive Play Rate, Points Per Drive)
    - Opponent defensive quality (EPA Allowed, Explosive Rate Allowed, PPD Allowed)
    - Implied team total
    - PROE (Pass Rate Over Expected) - pass-heavy teams more volatile, run-heavy more stable
    
    Returns multiplier to scale volatility (0.8 to 1.3 range).
    """
    
    # Team offensive factors
    team_epa = row.get('Team_EPA_Play', league_avgs['EPA_Play'])
    team_explosive = row.get('Team_Explosive_Play_Rate', league_avgs['Explosive_Play_Rate'])
    team_ppd = row.get('Team_Points_Per_Drive', league_avgs['Points_Per_Drive'])
    
    # For EPA (near-zero league avg), use additive difference scaled to reasonable range
    # EPA typically ranges from -0.20 to +0.20 around zero mean
    epa_diff = team_epa - league_avgs['EPA_Play']
    off_epa_factor = 1.0 + (epa_diff * 2.5)  # Scale to ±0.5 range
    
    # For other metrics, use ratios as normal
    off_explosive_factor = team_explosive / league_avgs['Explosive_Play_Rate'] if league_avgs['Explosive_Play_Rate'] != 0 else 1.0
    off_ppd_factor = team_ppd / league_avgs['Points_Per_Drive'] if league_avgs['Points_Per_Drive'] != 0 else 1.0
    
    # Average offensive factors
    off_factor_raw = (off_epa_factor + off_explosive_factor + off_ppd_factor) / 3.0
    
    # Opponent defensive factors
    opp_epa_allowed = row.get('Opp_EPA_Play_Allowed', league_avgs['EPA_Play_Allowed'])
    opp_explosive_allowed = row.get('Opp_Explosive_Play_Rate_Allowed', league_avgs['Explosive_Play_Rate_Allowed'])
    opp_ppd_allowed = row.get('Opp_Points_Per_Drive_Allowed', league_avgs['Points_Per_Drive_Allowed'])
    
    # For EPA Allowed, use additive difference (higher = worse defense = easier matchup)
    epa_allowed_diff = opp_epa_allowed - league_avgs['EPA_Play_Allowed']
    def_epa_factor = 1.0 + (epa_allowed_diff * 2.5)  # Scale to ±0.5 range
    
    # For other metrics, use ratios (higher = worse defense)
    def_explosive_factor = opp_explosive_allowed / league_avgs['Explosive_Play_Rate_Allowed'] if league_avgs['Explosive_Play_Rate_Allowed'] != 0 else 1.0
    def_ppd_factor = opp_ppd_allowed / league_avgs['Points_Per_Drive_Allowed'] if league_avgs['Points_Per_Drive_Allowed'] != 0 else 1.0
    
    # Average defensive factors
    def_factor_raw = (def_epa_factor + def_explosive_factor + def_ppd_factor) / 3.0
    
    # Implied team total factor
    itt = row.get('ITT', league_avgs['Implied_Total'])
    it_factor_raw = itt / league_avgs['Implied_Total'] if league_avgs['Implied_Total'] > 0 else 1.0
    
    # PROE factor (if available)
    proe_adjustment = 0.0
    if weekly_proe is not None and 'Team' in row:
        team_proe = calculate_weighted_proe(row['Team'], weekly_proe, lookback_weeks=8)
        # Convert PROE to adjustment:
        # Positive PROE (pass-heavy) → +volatility
        # Negative PROE (run-heavy) → -volatility
        # PROE typically ranges from -0.15 to +0.15
        # Scale to ±0.10 adjustment
        proe_adjustment = team_proe * 0.67
    
    # Weighted combination approach (avoids extreme multiplication)
    # Base = 1.0, then add/subtract based on factors
    # Off factor: ±20% weight
    # Def factor: ±20% weight  
    # ITT factor: ±15% weight
    # PROE: ±10% weight
    matchup_score = 1.0
    matchup_score += (off_factor_raw - 1.0) * 0.20
    matchup_score += (def_factor_raw - 1.0) * 0.20
    matchup_score += (it_factor_raw - 1.0) * 0.15
    matchup_score += proe_adjustment
    
    # Clamp to reasonable bounds (0.8 to 1.3)
    # Tough matchup/low total/run-heavy → 0.8 (less volatile)
    # Soft matchup/high total/pass-heavy → 1.3 (more volatile/upside)
    return np.clip(matchup_score, 0.8, 1.3)


# ============================================================================
# DISTRIBUTION BUILDING
# ============================================================================

def build_distributions(current_week_df: pd.DataFrame, 
                       player_volatility: pd.DataFrame,
                       league_avgs: dict,
                       weekly_proe: pd.DataFrame = None) -> pd.DataFrame:
    """
    Build lognormal distribution parameters for each player.
    
    Returns DataFrame with mu_log and sigma_log for simulation.
    """
    
    print("\nBuilding player distributions...")
    
    # Debug: Show sample data before merge
    print(f"  Current week players: {len(current_week_df)}")
    print(f"  Historical volatility records: {len(player_volatility)}")
    
    # Check for RBs in both datasets to debug the issue
    rb_in_slate = current_week_df[current_week_df['Position'] == 'RB']
    rb_in_vol = player_volatility[player_volatility['Position'] == 'RB']
    print(f"  RBs in slate: {len(rb_in_slate)}, RBs in volatility: {len(rb_in_vol)}")
    
    if len(rb_in_slate) > 0:
        print(f"  Sample RB in slate: Player='{rb_in_slate.iloc[0]['Player']}', Team='{rb_in_slate.iloc[0]['Team']}', Position='{rb_in_slate.iloc[0]['Position']}'")
    if len(rb_in_vol) > 0:
        print(f"  Sample RB in volatility: Player='{rb_in_vol.iloc[0]['Player']}', Team='{rb_in_vol.iloc[0]['Team']}', Position='{rb_in_vol.iloc[0]['Position']}'")
    
    # Check for DST in both datasets
    dst_in_slate = current_week_df[current_week_df['Position'].isin(['DST', 'D'])]
    dst_in_vol = player_volatility[player_volatility['Position'] == 'DST']
    print(f"  DST in slate: {len(dst_in_slate)}, DST in volatility: {len(dst_in_vol)}")
    
    if len(dst_in_slate) > 0 and len(dst_in_vol) > 0:
        print(f"  Sample DST in slate: Player='{dst_in_slate.iloc[0]['Player']}', Team='{dst_in_slate.iloc[0]['Team']}'")
        print(f"  Sample DST in volatility: Player='{dst_in_vol.iloc[0]['Player']}', Team='{dst_in_vol.iloc[0]['Team']}'")
    
    # Merge volatility data
    df = current_week_df.merge(
        player_volatility,
        on=['Player', 'Team', 'Position'],
        how='left'
    )
    
    # Check merge success and try multiple fallback strategies for mismatches
    missing_volatility = df['effective_std_fpts'].isna().sum()
    
    if missing_volatility > 0:
        print(f"  ⚠ {missing_volatility} players missing volatility after primary merge")
        
        # Strategy 1: Try fallback merge on Team + Position only
        missing_mask = df['effective_std_fpts'].isna()
        missing_indices = df[missing_mask].index
        
        print(f"  → Strategy 1: Matching on Team + Position for {len(missing_indices)} players...")
        
        for idx in missing_indices:
            if pd.notna(df.at[idx, 'effective_std_fpts']):
                continue  # Already filled
                
            player_name = df.at[idx, 'Player']
            team = df.at[idx, 'Team']
            position = df.at[idx, 'Position']
            
            # Find volatility records for same team + position
            candidates = player_volatility[
                (player_volatility['Team'] == team) & 
                (player_volatility['Position'] == position)
            ]
            
            if len(candidates) == 1:
                # Only one player at this position on this team - use it
                for col in ['hist_games', 'hist_mean_fpts', 'hist_std_fpts', 'effective_std_fpts', 
                           'hist_cv', 'hist_min_fpts', 'hist_max_fpts']:
                    df.at[idx, col] = candidates.iloc[0][col]
            elif len(candidates) > 1:
                # Multiple candidates - try case-insensitive name matching
                player_lower = player_name.lower().replace('.', '').replace("'", "").replace('-', '').replace(' ', '')
                
                for _, candidate in candidates.iterrows():
                    cand_lower = candidate['Player'].lower().replace('.', '').replace("'", "").replace('-', '').replace(' ', '')
                    
                    if player_lower == cand_lower:
                        # Found a match with normalized name
                        for col in ['hist_games', 'hist_mean_fpts', 'hist_std_fpts', 'effective_std_fpts', 
                                   'hist_cv', 'hist_min_fpts', 'hist_max_fpts']:
                            df.at[idx, col] = candidate[col]
                        break
        
        # Recheck missing count
        missing_volatility = df['effective_std_fpts'].isna().sum()
        matched = len(missing_indices) - missing_volatility
        if matched > 0:
            print(f"  ✓ Strategy 1 matched {matched} additional players")
    
    if missing_volatility > 0:
        print(f"  ⚠ {missing_volatility} players missing volatility data after merge")
        missing_players = df[df['effective_std_fpts'].isna()][['Player', 'Team', 'Position']]
        print(f"    Positions affected: {missing_players['Position'].value_counts().to_dict()}")
        
        # Show sample mismatches for debugging
        missing_rbs = missing_players[missing_players['Position'] == 'RB'].head(3)
        if len(missing_rbs) > 0:
            print(f"    Sample missing RBs:")
            for idx, row in missing_rbs.iterrows():
                print(f"      - '{row['Player']}' ({row['Team']}) - Position: {row['Position']}")
                # Check if player exists in volatility with different spelling
                vol_match = player_volatility[
                    (player_volatility['Position'] == 'RB') & 
                    (player_volatility['Team'] == row['Team'])
                ]
                if len(vol_match) > 0:
                    print(f"        Available RBs for {row['Team']}: {vol_match['Player'].tolist()}")
                else:
                    print(f"        No RBs found for {row['Team']} in volatility data")
    else:
        print(f"  ✓ All players successfully matched with volatility data")
    
    # For players without historical data, use position averages
    # Calculate position-level effective std
    pos_defaults = player_volatility.groupby('Position')['effective_std_fpts'].mean().to_dict()
    
    def get_effective_std(row):
        if pd.notna(row['effective_std_fpts']):
            return row['effective_std_fpts']
        else:
            return pos_defaults.get(row['Position'], 5.0)  # Default 5.0 if position unknown
    
    df['effective_std_fpts'] = df.apply(get_effective_std, axis=1)
    
    # Apply matchup adjustment using Sharp Football metrics and PROE
    df['matchup_vol_multiplier'] = df.apply(
        lambda row: compute_matchup_multiplier(row, league_avgs, weekly_proe), 
        axis=1
    )
    
    # Adjusted standard deviation
    df['adj_std'] = df['effective_std_fpts'] * df['matchup_vol_multiplier']
    
    # Apply min/max constraints
    df['adj_std'] = df['adj_std'].clip(ROOConfig.MIN_STD, ROOConfig.MAX_STD)
    
    # Convert to lognormal parameters
    # Goal: median ≈ OWS_Median_Proj, spread determined by adj_std
    
    def calc_lognormal_params(row):
        median_proj = max(row['OWS_Median_Proj'], ROOConfig.EPS)
        adj_std = row['adj_std']
        
        # Lognormal: median = exp(μ)
        mu_log = np.log(median_proj)
        
        # Sigma: use relative std to determine spread
        # rel_std captures how volatile the player is relative to their projection
        rel_std = adj_std / (median_proj + ROOConfig.EPS)
        
        # Convert to sigma using ln(1 + rel_std) heuristic
        # This ensures higher relative volatility → higher sigma
        sigma_log = np.log(1 + rel_std)
        
        # Clamp sigma to reasonable bounds
        sigma_log = np.clip(sigma_log, ROOConfig.MIN_SIGMA_LOG, ROOConfig.MAX_SIGMA_LOG)
        
        return pd.Series({'mu_log': mu_log, 'sigma_log': sigma_log})
    
    df[['mu_log', 'sigma_log']] = df.apply(calc_lognormal_params, axis=1)
    
    print(f"✓ Built distributions for {len(df)} players")
    print(f"  Avg sigma_log: {df['sigma_log'].mean():.3f}")
    print(f"  Avg adj_std: {df['adj_std'].mean():.1f}")
    
    return df


# ============================================================================
# MONTE CARLO SIMULATION
# ============================================================================

def run_simulations(players_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run Monte Carlo simulation to generate range of outcomes.
    
    Returns DataFrame with percentile projections added.
    """
    
    print(f"\nRunning {ROOConfig.N_SIMULATIONS:,} simulations...")
    
    # Set random seed
    np.random.seed(ROOConfig.RANDOM_SEED)
    
    # Extract arrays
    num_players = len(players_df)
    mu_arr = players_df['mu_log'].values
    sigma_arr = players_df['sigma_log'].values
    
    # Simulation matrix: [N_SIMULATIONS, num_players]
    sim_matrix = np.zeros((ROOConfig.N_SIMULATIONS, num_players))
    
    # Run simulations
    for i in range(ROOConfig.N_SIMULATIONS):
        if i % 2000 == 0 and i > 0:
            print(f"  Progress: {i:,} / {ROOConfig.N_SIMULATIONS:,} simulations")
        
        # Generate lognormal samples
        sim_matrix[i, :] = np.random.lognormal(mean=mu_arr, sigma=sigma_arr)
    
    print(f"✓ Completed {ROOConfig.N_SIMULATIONS:,} simulations")
    
    # Calculate percentiles
    print("\nCalculating percentiles...")
    percentile_values = np.percentile(sim_matrix, ROOConfig.PERCENTILES, axis=0)
    
    # Add percentiles to dataframe
    for i, pct in enumerate(ROOConfig.PERCENTILES):
        col_name = f'Sim_P{pct}'
        players_df[col_name] = percentile_values[i, :]
    
    # Define floor and ceiling
    players_df['Floor_Proj'] = players_df[f'Sim_P{ROOConfig.FLOOR_PERCENTILE}']
    players_df['Ceiling_Proj'] = players_df[f'Sim_P{ROOConfig.CEILING_PERCENTILE}']
    
    # Calculate volatility index (ceiling - floor) / median
    players_df['Volatility_Index'] = (
        (players_df['Ceiling_Proj'] - players_df['Floor_Proj']) / 
        (players_df['OWS_Median_Proj'] + 0.01)
    )
    
    print(f"✓ Calculated percentiles for all players")
    
    return players_df


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def generate_roo_projections(output_filename: str = "roo_projections.csv") -> pd.DataFrame:
    """
    Main pipeline to generate range-of-outcomes projections.
    
    Returns: DataFrame with floor/median/ceiling projections
    """
    
    print("="*70)
    print("NFL DFS Range-of-Outcomes (ROO) Simulation Engine")
    print("="*70)
    
    # 1. Load data
    data = load_data()
    
    # 2. Build historical volatility (players + DST)
    player_volatility = build_player_volatility(data['weekly_stats'], data['weekly_dst_stats'], data['player_mapping'])
    
    # 3. Build current week slate
    print("\nBuilding current week slate...")
    
    # Get current week from salaries
    current_week = data['salaries']['Week'].max()
    print(f"  Current week: {current_week}")
    
    # Current week salaries
    current_salaries = data['salaries'][data['salaries']['Week'] == current_week].copy()
    
    # DEBUG: Check what columns and data exist
    print(f"  Salaries columns: {current_salaries.columns.tolist()}")
    print(f"  Salaries shape: {current_salaries.shape}")
    print(f"  Sample salary IDs: {current_salaries['ID'].head(3).tolist() if 'ID' in current_salaries.columns else 'No ID column'}")
    print(f"  Sample salary Names: {current_salaries['Name'].head(3).tolist() if 'Name' in current_salaries.columns else 'No Name column'}")
    
    print(f"  Projections columns: {data['projections'].columns.tolist()}")
    print(f"  Projections shape: {data['projections'].shape}")
    print(f"  Sample projection Ids: {data['projections']['Id'].head(3).tolist() if 'Id' in data['projections'].columns else 'No Id column'}")
    print(f"  Sample projection Names: {data['projections']['Name'].head(3).tolist() if 'Name' in data['projections'].columns else 'No Name column'}")
    
    # Merge with projections by Name instead of ID (IDs don't match across sources)
    current_week_df = current_salaries.merge(
        data['projections'][['Name', 'Position', 'ProjPts', 'ProjOwn']],
        on='Name',
        how='inner',
        suffixes=('_salary', '_proj')
    )
    
    print(f"  After merge on Name: {len(current_week_df)} players matched")
    
    # Use projection name/position (more reliable), drop salary versions if they exist
    if 'Name_proj' in current_week_df.columns:
        current_week_df['Player'] = current_week_df['Name_proj']
        if 'Name_salary' in current_week_df.columns:
            current_week_df = current_week_df.drop(columns=['Name_salary'])
    elif 'Name' in current_week_df.columns:
        current_week_df['Player'] = current_week_df['Name']
    
    # Standardize player names using mapping (OneWeekSeason -> DK_Salaries)
    ows_to_dk_map = dict(zip(data['player_mapping']['OneWeekSeason'], data['player_mapping']['DK_Salaries']))
    current_week_df['Player'] = current_week_df['Player'].map(ows_to_dk_map).fillna(current_week_df['Player'])
    
    unmapped_proj = current_week_df[~current_week_df['Player'].isin(ows_to_dk_map.values())]['Player'].nunique()
    print(f"  {unmapped_proj} unique players in projections not in mapping (using original names)")
    
    if 'Position_proj' in current_week_df.columns:
        current_week_df['Position'] = current_week_df['Position_proj']
        if 'Position_salary' in current_week_df.columns:
            current_week_df = current_week_df.drop(columns=['Position_salary'])
    
    # Rename columns - be explicit about what exists
    rename_dict = {}
    if 'TeamAbbrev' in current_week_df.columns:
        rename_dict['TeamAbbrev'] = 'Team'
    if 'ProjPts' in current_week_df.columns:
        rename_dict['ProjPts'] = 'OWS_Median_Proj'
    if 'ProjOwn' in current_week_df.columns:
        rename_dict['ProjOwn'] = 'OWS_Proj_Own'
    
    current_week_df = current_week_df.rename(columns=rename_dict)
    
    # Drop duplicate Team column if it exists
    if 'Team_proj' in current_week_df.columns:
        current_week_df = current_week_df.drop(columns=['Team_proj'])
    if 'Team_salary' in current_week_df.columns:
        current_week_df = current_week_df.drop(columns=['Team_salary'])
    
    # Merge matchup data directly (more efficient than apply)
    matchup_data = data['matchups'][['Init', 'Opp', 'ITT', 'Spread', 'Loc']].copy()
    matchup_data = matchup_data.rename(columns={'Init': 'Team'})
    
    current_week_df = current_week_df.merge(
        matchup_data,
        on='Team',
        how='left'
    )
    
    # Fill missing matchup data with defaults
    current_week_df['Opp'] = current_week_df['Opp'].fillna('')
    current_week_df['ITT'] = current_week_df['ITT'].fillna(24.0)  # League avg
    current_week_df['Spread'] = current_week_df['Spread'].fillna(0)
    current_week_df['Loc'] = current_week_df['Loc'].fillna('Home')
    
    # Team abbreviation to full name mapping (for Sharp Football data)
    abbrev_to_full = {
        'ARI': 'Cardinals', 'ATL': 'Falcons', 'BAL': 'Ravens', 'BUF': 'Bills',
        'CAR': 'Panthers', 'CHI': 'Bears', 'CIN': 'Bengals', 'CLE': 'Browns',
        'DAL': 'Cowboys', 'DEN': 'Broncos', 'DET': 'Lions', 'GB': 'Packers',
        'HOU': 'Texans', 'IND': 'Colts', 'JAX': 'Jaguars', 'KC': 'Chiefs',
        'LAC': 'Chargers', 'LAR': 'Rams', 'LV': 'Raiders', 'MIA': 'Dolphins',
        'MIN': 'Vikings', 'NE': 'Patriots', 'NO': 'Saints', 'NYG': 'Giants',
        'NYJ': 'Jets', 'PHI': 'Eagles', 'PIT': 'Steelers', 'SEA': 'Seahawks',
        'SF': '49ers', 'TB': 'Buccaneers', 'TEN': 'Titans', 'WAS': 'Commanders'
    }
    
    # Create full name columns for merging with Sharp Football data
    current_week_df['Team_Full'] = current_week_df['Team'].map(abbrev_to_full).fillna(current_week_df['Team'])
    current_week_df['Opp_Full'] = current_week_df['Opp'].map(abbrev_to_full).fillna(current_week_df['Opp'])
    
    # Merge defensive metrics (for opponent)
    sharp_defense_renamed = data['sharp_defense'].rename(columns={
        'Team': 'Opp_Full',
        'EPA_Play_Allowed': 'Opp_EPA_Play_Allowed',
        'Explosive Play Rate Allowed': 'Opp_Explosive_Play_Rate_Allowed',
        'Points Per Drive Allowed': 'Opp_Points_Per_Drive_Allowed'
    })
    
    current_week_df = current_week_df.merge(
        sharp_defense_renamed[['Opp_Full', 'Opp_EPA_Play_Allowed', 'Opp_Explosive_Play_Rate_Allowed', 'Opp_Points_Per_Drive_Allowed']],
        on='Opp_Full',
        how='left'
    )
    
    # Merge team offensive metrics (for player's team)
    sharp_offense_renamed = data['sharp_offense'].rename(columns={
        'Team': 'Team_Full',
        'EPA_Play': 'Team_EPA_Play',
        'Explosive Play Rate': 'Team_Explosive_Play_Rate',
        'Points Per Drive': 'Team_Points_Per_Drive'
    })
    
    current_week_df = current_week_df.merge(
        sharp_offense_renamed[['Team_Full', 'Team_EPA_Play', 'Team_Explosive_Play_Rate', 'Team_Points_Per_Drive']],
        on='Team_Full',
        how='left'
    )
    
    # Drop the temporary full name columns
    current_week_df = current_week_df.drop(columns=['Team_Full', 'Opp_Full'])
    
    # Rename defensive columns to have 'Opp_' prefix (already done above, but keep for safety)
    # Remove the old renaming code since we did it before the merge
    
    # Fill missing team offensive metrics with league averages (will be calculated below)
    # For now, fill with 0 to avoid errors
    for col in ['Team_EPA_Play', 'Team_Explosive_Play_Rate', 'Team_Points_Per_Drive']:
        if col in current_week_df.columns:
            current_week_df[col] = current_week_df[col].fillna(0)
    
    for col in ['Opp_EPA_Play_Allowed', 'Opp_Explosive_Play_Rate_Allowed', 'Opp_Points_Per_Drive_Allowed']:
        if col in current_week_df.columns:
            current_week_df[col] = current_week_df[col].fillna(0)
    
    # Filter to players with projections > 0
    current_week_df = current_week_df[current_week_df['OWS_Median_Proj'] > 0].copy()
    
    # Normalize DST position names (DraftKings uses 'D', we use 'DST')
    current_week_df['Position'] = current_week_df['Position'].replace({'D': 'DST'})
    
    dst_count = (current_week_df['Position'] == 'DST').sum()
    print(f"✓ Built slate with {len(current_week_df)} players (including {dst_count} DST)")
    
    # Show sample player names from current slate
    sample_rbs = current_week_df[current_week_df['Position'] == 'RB']['Player'].head(5).tolist()
    if sample_rbs:
        print(f"  Sample RBs in slate: {sample_rbs}")
    
    # Debug: Check if Player column exists
    if 'Player' not in current_week_df.columns:
        print(f"⚠ Warning: 'Player' column missing. Available columns: {list(current_week_df.columns[:10])}")
        # Try to find the player name column
        if 'Name' in current_week_df.columns:
            current_week_df['Player'] = current_week_df['Name']
            print("  Using 'Name' column as 'Player'")
        elif 'Name_salary' in current_week_df.columns:
            current_week_df['Player'] = current_week_df['Name_salary']
            print("  Using 'Name_salary' column as 'Player'")
        else:
            raise ValueError("Cannot find player name column!")
    
    # Check if Position column exists properly
    if 'Position' not in current_week_df.columns:
        if 'Position_salary' in current_week_df.columns:
            current_week_df['Position'] = current_week_df['Position_salary']
            print("  Using 'Position_salary' column as 'Position'")
    
    # Calculate league averages for Sharp metrics
    print("\nCalculating league averages for normalization...")
    league_avgs = compute_league_averages(
        data['sharp_offense'],
        data['sharp_defense'],
        data['matchups']
    )
    print(f"  League avg ITT: {league_avgs['Implied_Total']:.1f}")
    print(f"  League avg EPA/Play: {league_avgs['EPA_Play']:.3f}")
    
    # 4. Build distributions
    players_with_dist = build_distributions(current_week_df, player_volatility, league_avgs, data['weekly_proe'])
    
    # 5. Run simulations
    results_df = run_simulations(players_with_dist)
    
    # 6. Prepare output
    print("\nPreparing output...")
    
    output_cols = [
        'Player', 'Team', 'Position', 'Salary', 'Opp', 'ITT', 'Spread', 'Loc',
        'OWS_Median_Proj', 'OWS_Proj_Own',
        'Floor_Proj', 'Ceiling_Proj',
        'Sim_P10', 'Sim_P15', 'Sim_P25', 'Sim_P50', 'Sim_P75', 'Sim_P85', 'Sim_P90', 'Sim_P95',
        'Volatility_Index',
        'hist_games', 'hist_mean_fpts', 'hist_std_fpts', 'hist_max_fpts', 'effective_std_fpts',
        'matchup_vol_multiplier', 'adj_std'
    ]
    
    # Filter to available columns
    output_cols = [col for col in output_cols if col in results_df.columns]
    output_df = results_df[output_cols].copy()
    
    # Sort by position and salary
    position_order = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4, 'DST': 5}
    output_df['pos_sort'] = output_df['Position'].map(position_order)
    output_df = output_df.sort_values(['pos_sort', 'Salary'], ascending=[True, False])
    output_df = output_df.drop(columns=['pos_sort'])
    
    # 7. Save output
    output_path = Path(ROOConfig.DATA_DIR) / output_filename
    output_df.to_csv(output_path, index=False)
    
    print(f"\n✓ Saved ROO projections to: {output_path}")
    print(f"  Total players: {len(output_df)}")
    
    # 8. Print summary stats
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    
    for pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
        pos_df = output_df[output_df['Position'] == pos]
        if len(pos_df) > 0:
            print(f"\n{pos}:")
            print(f"  Count: {len(pos_df)}")
            print(f"  Avg Ceiling: {pos_df['Ceiling_Proj'].mean():.1f}")
            print(f"  Max Ceiling: {pos_df['Ceiling_Proj'].max():.1f} ({pos_df.loc[pos_df['Ceiling_Proj'].idxmax(), 'Player']})")
            print(f"  Avg Floor: {pos_df['Floor_Proj'].mean():.1f}")
            print(f"  Avg Volatility Index: {pos_df['Volatility_Index'].mean():.2f}")
    
    print("\n" + "="*70)
    print("ROO SIMULATION COMPLETE!")
    print("="*70)
    
    return output_df


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Optional: accept output filename from command line
    output_file = sys.argv[1] if len(sys.argv) > 1 else "roo_projections.csv"
    
    # Run simulation
    results = generate_roo_projections(output_file)
    
    print(f"\nResults available in variable: results")
    print(f"Shape: {results.shape}")
