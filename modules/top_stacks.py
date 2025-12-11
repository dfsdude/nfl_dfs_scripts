import streamlit as st
import pandas as pd
import numpy as np
import math
import itertools
import os
from pathlib import Path
from scipy import stats

# Import data loader
try:
    import sys
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    from data.data_loader import load_matchups
    DATA_LOADER_AVAILABLE = True
except ImportError:
    DATA_LOADER_AVAILABLE = False

# Import correlation module
try:
    from correlation_model import (
        build_team_player_roles,
        compute_team_correlations,
        get_correlation_rag,
        get_correlation_label
    )
    CORRELATION_AVAILABLE = True
except ImportError:
    CORRELATION_AVAILABLE = False


# --------------------------------------------------------
# Game Script Analysis Functions
# --------------------------------------------------------
def calculate_game_script(players_df):
    """
    Calculate game script projections based on spread, total, and implied team total.
    
    Game Script Categories:
    - Blowout: High probability of lopsided game (spread magnitude > 7)
    - Competitive: Close game expected (spread magnitude <= 7, total < 50)
    - Shootout: High-scoring affair (total >= 50)
    - Low-Scoring: Defensive struggle (total < 44, spread close)
    
    Returns dataframe with added columns:
    - script_cat: Game script category
    - blowout_prob: Probability of 14+ point margin
    - script_impact: Position-specific fantasy impact multiplier
    """
    df = players_df.copy()
    
    # Calculate blowout probability (spread distribution, std dev ~13.5 points)
    # Probability that final margin exceeds 14 points (2 possession game)
    df['blowout_prob'] = df['spread'].apply(lambda s: 
        1 - stats.norm.cdf(14, loc=abs(s), scale=13.5) if pd.notna(s) else 0
    )
    
    # Determine game script category
    def categorize_script(row):
        spread = abs(row.get('spread', 0))
        total = row.get('game_total', 0)
        itt = row.get('implied_total', 0)
        
        # Blowout: Large spread (>7 pts)
        # Note: Negative spread = favorite, Positive spread = underdog
        if spread > 7:
            if row.get('spread', 0) < 0:  # Negative spread = Favorite
                return "🔥 Blowout (Fav)"
            else:  # Positive spread = Underdog
                return "❄️ Blowout (Dog)"
        
        # Shootout: High total (50+ points)
        elif total >= 50:
            return "⚡ Shootout"
        
        # Low-Scoring: Low total (<44 points)
        elif total < 44:
            return "🛡️ Low-Scoring"
        
        # Competitive: Everything else (close spread, moderate total)
        else:
            return "⚖️ Competitive"
    
    df['script_cat'] = df.apply(categorize_script, axis=1)
    
    # Calculate position-specific script impact
    def calculate_script_impact(row):
        """
        Adjust fantasy ceiling based on game script and position.
        
        Position impacts by script:
        - QB: Best in shootouts (+15%), worst in low-scoring (-10%)
        - RB: Best as favorite in blowout (+20%), worst as underdog (-15%)
        - WR: Best in shootouts (+12%), decent in competitive (+5%)
        - TE: Relatively script-neutral, slight boost in competitive (+5%)
        - DST: Best in opponent blowout (dog) (+25%), worst in shootouts (-20%)
        """
        position = row.get('position', '')
        script = row.get('script_cat', '')
        spread = row.get('spread', 0)
        
        # Default neutral impact
        impact = 1.0
        
        if 'Blowout (Fav)' in script:
            if position == 'RB': impact = 1.20  # Run-heavy game script
            elif position == 'QB': impact = 1.05  # Steady but not shootout
            elif position == 'WR': impact = 0.95  # Fewer attempts
            elif position == 'TE': impact = 1.00  # Neutral
            elif position == 'DST': impact = 0.80  # Likely to give up points
        
        elif 'Blowout (Dog)' in script:
            if position == 'RB': impact = 0.85  # Game script away from run
            elif position == 'QB': impact = 1.10  # Garbage time passing
            elif position == 'WR': impact = 1.08  # Volume in catchup mode
            elif position == 'TE': impact = 1.05  # Safety valve targets
            elif position == 'DST': impact = 1.25  # Sacks, turnovers likely
        
        elif 'Shootout' in script:
            if position == 'QB': impact = 1.15  # Optimal script
            elif position == 'WR': impact = 1.12  # High volume passing
            elif position == 'RB': impact = 1.05  # Some volume but pass-heavy
            elif position == 'TE': impact = 1.08  # Red zone targets
            elif position == 'DST': impact = 0.80  # High points allowed
        
        elif 'Low-Scoring' in script:
            if position == 'DST': impact = 1.15  # Defensive struggle
            elif position == 'RB': impact = 1.05  # Run-heavy game
            elif position == 'QB': impact = 0.90  # Limited attempts
            elif position == 'WR': impact = 0.92  # Fewer targets
            elif position == 'TE': impact = 0.95  # Limited volume
        
        else:  # Competitive
            if position == 'TE': impact = 1.05  # Steady targets
            elif position == 'WR': impact = 1.05  # Balanced attack
            elif position == 'QB': impact = 1.02  # Normal game flow
            elif position == 'RB': impact = 1.02  # Balanced usage
            elif position == 'DST': impact = 1.00  # Neutral
        
        return impact
    
    df['script_impact'] = df.apply(calculate_script_impact, axis=1)
    
    return df


# --------------------------------------------------------
# Configuration Constants
# --------------------------------------------------------
class DFSConfig:
    """Centralized configuration for DFS analysis"""
    
    # Data directory (can be overridden via environment variable)
    DATA_DIR = os.getenv("DFS_DATA_DIR", r"C:\Users\schne\Documents\DFS\2025\Dashboard")
    
    # Position roster constraints (DraftKings)
    POSITION_MIN_REQUIREMENTS = {
        "QB": 100,   # 1 required
        "RB": 200,   # 2 required
        "WR": 300,   # 3 required
        "TE": 100,   # 1 required
        "DST": 100,  # 1 required
    }
    
    # Player pool targets for 20-lineup GPP
    POOL_TARGETS = {
        "QB": 4,
        "RB": 8,
        "WR": 15,
        "TE": 7,
        "DST": 5,
        "D": 5
    }
    
    # Maximum acceptable pool sizes (before auto-trimming)
    POOL_MAX_ACCEPTABLE = {
        "QB": 4,   # Upper end of 3-4 range
        "RB": 8,   # Upper end of 6-8 range
        "WR": 15,  # Upper end of 12-15 range
        "TE": 7,   # Upper end of 4-7 range
        "DST": 5,  # Upper end of 4-5 range
    }
    
    # Percentile thresholds
    CEILING_PERCENTILE_LOW = 0.33   # Bottom third
    CEILING_PERCENTILE_HIGH = 0.67  # Top third
    BOOM_THRESHOLD_PERCENTILE = 0.95
    
    # Matchup adjustment bounds (using Sharp EPA metrics)
    EPA_FACTOR_MIN = 0.8  # Maximum penalty for tough matchup
    EPA_FACTOR_MAX = 1.2  # Maximum boost for great matchup
    
    # Required CSV columns (updated for new file structure)
    REQUIRED_MATCHUP_COLS = ["Init", "Opp", "ITT", "Loc", "FavStatus", "Spread"]
    REQUIRED_WEEKLY_STATS_COLS = ["Player", "Position", "Team", "Weighted_Opportunities"]
    REQUIRED_SALARY_COLS = ["Name", "TeamAbbrev", "Salary", "Position"]
    REQUIRED_PROJECTIONS_COLS = ["Id", "Name", "Position", "ProjPts", "ProjOwn"]

# --------------------------------------------------------
# Helper: Normal CDF (no SciPy needed)
# --------------------------------------------------------
def normal_cdf(x, mean, std):
    if std <= 0 or pd.isna(std):
        return float(x >= mean)
    z = (x - mean) / std
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# --------------------------------------------------------
# Percentile-based boom threshold function
# --------------------------------------------------------
def get_boom_threshold(position, salary):
    """Return boom threshold based on position and salary tier (95th percentile targets)
    Calibrated to align with 230+ point GPP winning lineups"""
    sal_k = salary / 1000.0
    
    if position == "QB":
        if sal_k >= 7.0:
            return 35.0  # Elite QB boom
        elif sal_k >= 6.0:
            return 28.0  # Mid-tier QB boom
        else:
            return 22.0  # Value QB boom
    
    elif position == "RB":
        if sal_k >= 8.0:
            return 32.0  # Elite RB boom
        elif sal_k >= 6.5:
            return 25.0  # Mid-tier RB boom
        else:
            return 18.0  # Value RB boom
    
    elif position == "WR":
        if sal_k >= 8.0:
            return 35.0  # Elite WR boom
        elif sal_k >= 6.5:
            return 28.0  # Mid-tier WR boom
        else:
            return 20.0  # Value WR boom
    
    elif position == "TE":
        if sal_k >= 6.0:
            return 28.0  # Elite TE boom
        elif sal_k >= 5.0:
            return 22.0  # Mid-tier TE boom
        else:
            return 16.0  # Value TE boom
    
    elif position in ["DST", "D"]:
        if sal_k >= 4.0:
            return 18.0  # Strong DST boom
        elif sal_k >= 3.0:
            return 14.0  # Mid-tier DST boom
        else:
            return 10.0  # Value DST boom
    
    # Fallback (should not happen)
    return 4.0 * sal_k


# --------------------------------------------------------
# 1. Load projections and matchup files
# --------------------------------------------------------
@st.cache_data
def load_data():
    """Load and validate all data files - uses ROO projections as primary source"""
    try:
        data_dir = Path(DFSConfig.DATA_DIR)
        
        # Try to load ROO projections first (primary source)
        roo_file = data_dir / "roo_projections.csv"
        
        if roo_file.exists():
            st.info("✅ Using ROO projections as primary data source")
            
            # Load ROO projections (has everything we need!)
            players = pd.read_csv(roo_file)
            matchups = load_matchups() if DATA_LOADER_AVAILABLE else pd.read_csv(data_dir / "Matchup.csv")
            sharp_offense = pd.read_csv(data_dir / "sharp_offense.csv")
            sharp_defense = pd.read_csv(data_dir / "sharp_defense.csv")
            weekly_proe = pd.read_csv(data_dir / "weekly_proe_2025.csv")
            weekly_stats = pd.read_csv(data_dir / "Weekly_Stats.csv")
            weekly_dst_stats = pd.read_csv(data_dir / "Weekly_DST_Stats.csv")
            
            # Load or compute correlation scores
            team_correlations = None
            if CORRELATION_AVAILABLE:
                try:
                    st.info("📊 Computing player correlations...")
                    roles_df = build_team_player_roles(weekly_stats)
                    team_correlations = compute_team_correlations(weekly_stats, roles_df, min_weeks=4)
                    st.success(f"✅ Computed correlations for {len(team_correlations)} teams")
                except Exception as e:
                    st.warning(f"⚠️ Could not compute correlations: {str(e)}")
                    team_correlations = None
            
            # Concentration module removed - not using 2024 data for 2025 season
            concentration_df = None
            
            # Rename ROO columns to match expected format
            players = players.rename(columns={
                'Player': 'name',
                'Team': 'team',
                'Position': 'position',
                'Salary': 'salary',
                'Opp': 'opponent',
                'OWS_Median_Proj': 'proj',
                'OWS_Proj_Own': 'dk_ownership',
                'Ceiling_Proj': 'ceiling_ows',
                'Floor_Proj': 'floor_25',
                'Sim_P75': 'ceil_75',
                'effective_std_fpts': 'stddev',
                'Volatility_Index': 'volatility_index',
                'hist_max_fpts': 'max_dk',
                'hist_mean_fpts': 'avg_dk'
            })
            
            # Add derived columns that might be missing
            if 'var_dk' not in players.columns:
                players['var_dk'] = players['stddev'] ** 2 if 'stddev' in players.columns else players['proj'] * 0.5
            
            if 'stddev' not in players.columns:
                players['stddev'] = np.sqrt(players['var_dk'])
            
            # Only add max_dk and avg_dk if they weren't loaded from ROO projections
            if 'max_dk' not in players.columns:
                players['max_dk'] = players['ceiling_ows']
            
            if 'avg_dk' not in players.columns:
                players['avg_dk'] = players['proj']
            
            # Calculate hits_4x from Weekly_Stats.csv and Weekly_DST_Stats.csv
            # Count how many times each player scored 4x their current salary
            if 'hits_4x' not in players.columns:
                hits_4x_dict = {}
                for _, player_row in players.iterrows():
                    player_name = player_row['name']
                    player_position = player_row.get('position', '')
                    current_salary = player_row['salary']
                    target_points = (current_salary / 1000.0) * 4  # 4x value threshold
                    
                    # Use appropriate data source based on position
                    if player_position == 'DST':
                        # Get DST historical games from Weekly_DST_Stats
                        player_games = weekly_dst_stats[
                            (weekly_dst_stats['Player'] == player_name) &
                            (weekly_dst_stats['DK_Points'].notna())
                        ]
                    else:
                        # Get player's historical games from Weekly_Stats (QB, RB, WR, TE)
                        player_games = weekly_stats[
                            (weekly_stats['Player'] == player_name) &
                            (weekly_stats['DK_Points'].notna())
                        ]
                    
                    # Count games where DK_Points >= 4x current salary
                    hits = len(player_games[player_games['DK_Points'] >= target_points])
                    hits_4x_dict[player_name] = hits
                
                players['hits_4x'] = players['name'].map(hits_4x_dict).fillna(0).astype(int)
            
            if 'weighted_opp' not in players.columns:
                players['weighted_opp'] = 0
            
            # Add game context from matchups
            spread_dict = matchups.set_index("Init")["Spread"].to_dict()
            players["spread"] = players["team"].map(spread_dict).fillna(0)
            
            loc_dict = matchups.set_index("Init")["Loc"].to_dict()
            players["is_home"] = players["team"].map(loc_dict).apply(
                lambda x: x == "Home" if pd.notna(x) else False
            )
            
            itt_dict = matchups.set_index("Init")["ITT"].to_dict()
            players["implied_total"] = players["team"].map(itt_dict).fillna(0)
            
            # Add game total for each team
            total_dict = matchups.set_index("Init")["Total"].to_dict()
            players["game_total"] = players["team"].map(total_dict).fillna(0)
            
            # Calculate game script projections
            players = calculate_game_script(players)
            
            # Add PROE data (Pass Rate Over Expected)
            # Get current week's PROE data
            current_week_proe = weekly_proe[weekly_proe["week"] == weekly_proe["week"].max()].copy()
            proe_dict = current_week_proe.set_index("posteam")["proe"].to_dict()
            players["proe"] = players["team"].map(proe_dict).fillna(0)
            
        else:
            # Fallback to legacy data loading
            st.warning("⚠️ ROO projections not found, using legacy data sources")
            
            matchups = load_matchups() if DATA_LOADER_AVAILABLE else pd.read_csv(data_dir / "Matchup.csv")
            weekly_stats = pd.read_csv(data_dir / "Weekly_Stats.csv")
            sharp_offense = pd.read_csv(data_dir / "sharp_offense.csv")
            sharp_defense = pd.read_csv(data_dir / "sharp_defense.csv")
            salaries = pd.read_csv(data_dir / "Salaries_2025.csv")
            projections = pd.read_csv(data_dir / "ows_projections.csv")
            
            # [Keep existing legacy loading code here as fallback]
            # Get current week's salaries
            current_week = salaries["Week"].max()
            current_salaries = salaries[salaries["Week"] == current_week].copy()
            
            # Merge with projections
            current_salaries = current_salaries.merge(
                projections,
                left_on="ID",
                right_on="Id",
                how="left",
                suffixes=("_salary", "_proj")
            )
            
            # Calculate historical stats
            recent_weeks = weekly_stats["Week"].max()
            lookback_weeks = 4
            recent_stats = weekly_stats[weekly_stats["Week"] > (recent_weeks - lookback_weeks)].copy()
            
            player_agg = recent_stats.groupby(["Player", "Position", "Team"]).agg({
                "DK_Points": ["max", "std"],
                "Weighted_Opportunities": "mean"
            }).reset_index()
            
            player_agg.columns = ["Player", "Position", "Team", "ceiling_hist", "var_dk_std", "weighted_opp"]
            player_agg["var_dk"] = player_agg["var_dk_std"] ** 2
            player_agg['ceiling_proj'] = player_agg['ceiling_hist']
            
            players = current_salaries.merge(
                player_agg,
                left_on=["Name_proj", "Position_proj", "TeamAbbrev"],
                right_on=["Player", "Position", "Team"],
                how="left"
            )
            
            players = players.rename(columns={
                "Name_proj": "name",
                "Position_proj": "position",
                "TeamAbbrev": "team",
                "Salary": "salary",
                "ProjPts": "proj",
                "ProjOwn": "dk_ownership",
                "AvgPointsPerGame": "avg_dk",
            })
            
            players["ceiling_ows"] = players["ceiling_proj"].fillna(players["proj"] * 1.5)
            players["max_dk"] = players["ceiling_ows"]
            players["var_dk"] = players["var_dk"].fillna(players["proj"] * 0.5)
            players["weighted_opp"] = players["weighted_opp"].fillna(0)
            players["hits_4x"] = 0
            
            players = players.dropna(subset=["name", "position", "team", "salary", "proj"])
            players["dk_ownership"] = players["dk_ownership"] / 100.0
            players["stddev"] = np.sqrt(players["var_dk"])
            
            matchup_dict_temp = matchups.set_index("Init")["Opp"].to_dict()
            players["opponent"] = players["team"].map(matchup_dict_temp)
            
            spread_dict = matchups.set_index("Init")["Spread"].to_dict()
            players["spread"] = players["team"].map(spread_dict).fillna(0)
            
            loc_dict = matchups.set_index("Init")["Loc"].to_dict()
            players["is_home"] = players["team"].map(loc_dict).apply(
                lambda x: x == "Home" if pd.notna(x) else False
            )
            
            itt_dict = matchups.set_index("Init")["ITT"].to_dict()
            players["implied_total"] = players["team"].map(itt_dict).fillna(0)
            
            # Add PROE data (Pass Rate Over Expected)
            try:
                weekly_proe = pd.read_csv(data_dir / "weekly_proe_2025.csv")
                current_week_proe = weekly_proe[weekly_proe["week"] == weekly_proe["week"].max()].copy()
                proe_dict = current_week_proe.set_index("posteam")["proe"].to_dict()
                players["proe"] = players["team"].map(proe_dict).fillna(0)
            except FileNotFoundError:
                st.warning("⚠️ PROE data not found, using default values")
                players["proe"] = 0
            
    except FileNotFoundError as e:
        st.error(f"❌ **Data File Not Found**: {e}\n\nPlease ensure data files are in: `{DFSConfig.DATA_DIR}`")
        st.info("💡 Set environment variable `DFS_DATA_DIR` to change data directory location")
        st.stop()
    except ValueError as e:
        st.error(f"❌ **Data Validation Error**: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ **Unexpected Error Loading Data**: {e}")
        st.stop()
    
    # Clean up and validate data
    players = players.dropna(subset=["name", "position", "team", "salary", "proj"])
    
    # Ensure ownership is in decimal format (0-1 range)
    if players["dk_ownership"].max() > 1.5:
        players["dk_ownership"] = players["dk_ownership"] / 100.0
    
    # Use ROO simulated values directly (already includes matchup adjustments)
    # proj_adj = base projection (OWS_Median_Proj from ROO)
    # ceiling_adj = ROO Ceiling_Proj (P85 from 10k simulations with matchup multipliers)
    # stddev_adj = ROO effective_std_fpts (includes matchup volatility adjustment)
    players["proj_adj"] = players["proj"]
    players["ceiling_adj"] = players["ceiling_ows"]  # Already renamed from Ceiling_Proj
    players["stddev_adj"] = players["stddev"]  # Already renamed from effective_std_fpts
    
    # floor_25 and ceil_75 already come from ROO (Floor_Proj and Sim_P75)
    # No need to recalculate with z-scores
    
    # Boom/Bust calculation
    pos_bust_mult = {
        "QB": 2.0,
        "RB": 2.3,
        "WR": 2.3,
        "TE": 2.0,
        "DST": 1.8,
        "D": 1.8,
    }
    
    boom_probs = []
    bust_probs = []
    
    for _, row in players.iterrows():
        pos = row["position"]
        sal = row["salary"]
        sal_k = sal / 1000.0
        mean = row["proj_adj"]  # Base projection
        std = row["stddev_adj"]  # ROO simulated std (includes matchup volatility)
        
        boom_target = get_boom_threshold(pos, sal)
        bust_x = pos_bust_mult.get(pos, 2.2)
        bust_target = bust_x * sal_k
        
        bust_prob = normal_cdf(bust_target, mean, std)
        boom_prob = 1.0 - normal_cdf(boom_target, mean, std)
        
        bust_probs.append(min(max(bust_prob, 0), 1))
        boom_probs.append(min(max(boom_prob, 0), 1))
    
    players["bust_prob"] = bust_probs
    players["boom_prob"] = boom_probs
    players["leverage_boom"] = players["boom_prob"] - players["dk_ownership"]
    
    # For stacks (use adjusted values)
    players["dk"] = players["proj_adj"]
    players["dk_ceiling"] = players["ceiling_adj"]
    
    # Matchup dictionaries
    matchup_dict = matchups.set_index("Init")["Opp"].to_dict()
    matchup_expanded = matchups.set_index("Init").to_dict(orient="index")
    
    # Team offense/defense dictionaries (using Sharp metrics)
    team_offense_dict = sharp_offense.set_index("Team").to_dict(orient="index")
    team_defense_dict = sharp_defense.set_index("Team").to_dict(orient="index")
    
    # Concentration feature removed
    
    return players, matchups, matchup_dict, matchup_expanded, team_offense_dict, team_defense_dict, team_correlations


df, matchups, matchup_dict, matchup_expanded, team_offense_dict, team_defense_dict, team_correlations = load_data()
concentration_df = None  # Removed concentration feature


# --------------------------------------------------------
# Streamlit Page Config
# --------------------------------------------------------
# Disabled for unified app - page config set in main app.py
# st.set_page_config(page_title="NFL Top Stacks + Boom/Bust Tool", layout="wide")

def run():
    """Main entry point for Top Stacks & Boom/Bust Tool"""

    st.title("🏈 NFL Top Stacks + Boom/Bust Tool")
    st.caption("Player-level Boom/Bust model + matchup-aware stack explorer")

    # Sidebar filters
    st.sidebar.title("⚙️ Configuration")

    # Correlation Settings
    with st.sidebar.expander("📊 Correlation Settings (Advanced)", expanded=False):
        st.caption("Adjust correlation between stacked players for more accurate boom probability")
        corr_qb_pass = st.slider(
            "QB ↔ Pass Catcher",
            0.0, 0.8, 0.35, 0.05,
            help="Higher = QB & receivers score together more often (0.3-0.5 typical)",
            key="corr_qb_pass"
        )
        corr_pass_pass = st.slider(
            "Pass Catcher ↔ Pass Catcher",
            -0.3, 0.3, 0.05, 0.05,
            help="Usually low/negative due to target competition",
            key="corr_pass_pass"
        )
        st.info("💡 Higher correlation = higher stack variance = higher boom probability")

    # No player filters - use all players with automated logic
    df_filtered = df.copy()


    # --------------------------------------------------------
    # Intuitive View Switching with Radio Selector
    # --------------------------------------------------------
    st.markdown("## 🏈 NFL DFS Stack Analyzer")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        view_mode = st.radio(
            "Select View:",
            ["📊 Player Boom/Bust", "🧱 Top Stacks", "⚔️ Game Matchups"],
            horizontal=True,
            label_visibility="collapsed",
            key="view_mode"
        )

    st.divider()


    # --------------------------------------------------------
    # Stack Builder (with True Stack Boom Model + Leverage)
    # --------------------------------------------------------
    def get_stack(df_in, matchup_dict, stack_type, stack_positions, bringback_positions):

        pos_boom_mult = {
            "QB": 4.0,
            "RB": 4.0,
            "WR": 4.0,
            "TE": 4.0,
            "DST": 3.0,
            "D": 3.0,
        }

        qbs = df_in[df_in["position"] == "QB"]
        results = []
        
        # Pre-compute Weekly_Stats pace data ONCE instead of per-stack
        pace_data = {}
        rush_pct_data = {}
        pass_att_data = {}
        try:
            data_dir = Path(DFSConfig.DATA_DIR)
            weekly_stats = pd.read_csv(data_dir / "Weekly_Stats.csv")
            recent_weeks = weekly_stats["Week"].max()
            lookback = 4
            recent_stats = weekly_stats[weekly_stats["Week"] > (recent_weeks - lookback)].copy()
        
            team_pace = recent_stats.groupby("Team").agg({
                "Pass_Att": "sum",
                "Rush_Att": "sum"
            }).reset_index()
        
            team_pace["Total_Plays"] = team_pace["Pass_Att"] + team_pace["Rush_Att"]
            team_pace["Plays_Per_Game"] = (team_pace["Total_Plays"] / lookback)
            
            # Pre-build dictionaries for fast lookup
            for _, row in team_pace.iterrows():
                team = row["Team"]
                pace_data[team] = float(row["Plays_Per_Game"])
                pass_att_data[team] = float(row["Pass_Att"]) / lookback
                total = float(row["Total_Plays"])
                rush = float(row["Rush_Att"])
                rush_pct_data[team] = (rush / total) * 100 if total > 0 else 50.0
        except:
            pass  # Will use defaults

        for _, qb in qbs.iterrows():
            team = qb["team"]

            if team not in matchup_dict:
                continue

            opp = matchup_dict[team]

            # Expanded matchup data
            team_matchup = matchup_expanded.get(team, {})
            opp_matchup = matchup_expanded.get(opp, {})

            team_skill = df_in[
                (df_in["team"] == team)
                & (df_in["position"].isin(stack_positions))
                & (df_in["name"] != qb["name"])
            ]

            opp_skill = df_in[
                (df_in["team"] == opp)
                & (df_in["position"].isin(bringback_positions))
            ]

            if team_skill.empty:
                continue

            # Determine stack size
            if "+1" in stack_type:
                team_size = 1
            elif "+2" in stack_type:
                team_size = 2
            else:
                team_size = 3

            # Convert to list of dicts once
            team_skill_list = team_skill.to_dict("records")
            team_combos = list(itertools.combinations(team_skill_list, team_size))

            # Pre-sort bring-back candidates once (if needed)
            bringback_candidates = []
            if "One Bringback" in stack_type:
                if opp_skill.empty:
                    continue  # Skip this QB entirely if no bring-back options
            
                # Calculate leverage score: (Boom% - Own%) weighted with ceiling upside
                # This identifies high-upside, low-owned bring-back plays
                opp_skill_copy = opp_skill.copy()
                opp_skill_copy['bb_leverage_score'] = (
                    (opp_skill_copy['boom_prob'] * 100 - opp_skill_copy['dk_ownership'] * 100) * 0.6 +
                    (opp_skill_copy['dk_ceiling'] - opp_skill_copy['dk']) * 0.4
                )
            
                # Get top 3 bring-back candidates for variety
                bringback_candidates = (
                    opp_skill_copy
                    .sort_values('bb_leverage_score', ascending=False)
                    .head(3)
                    .to_dict('records')
                )
            
            # Pre-compute Sharp Football metrics for this matchup ONCE
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
        
            team_full = abbrev_to_full.get(team, team)
            opp_full = abbrev_to_full.get(opp, opp)
        
            team_off_data = team_offense_dict.get(team_full, {})
            opp_def_data = team_defense_dict.get(opp_full, {})
            
            # Pre-compute matchup metrics once per QB
            try:
                epa_adv = float(team_off_data.get("EPA_Play", 0)) - float(opp_def_data.get("EPA_Play_Allowed", 0))
                ypp_adv = float(team_off_data.get("Yards Per Play", 0)) - float(opp_def_data.get("Yards Per Play Allowed", 0))
                ptd_adv = float(team_off_data.get("Points Per Drive", 0)) - float(opp_def_data.get("Points Per Drive Allowed", 0))
                exp_adv = float(team_off_data.get("Explosive Play Rate", 0)) - float(opp_def_data.get("Explosive Play Rate Allowed", 0))
                dcr_adv = float(team_off_data.get("Down Conversion Rate", 0)) - float(opp_def_data.get("Down Conversion Rate Allowed", 0))
            except Exception:
                epa_adv = ypp_adv = ptd_adv = exp_adv = dcr_adv = 0.0
            
            # Pre-compute game environment score once per QB
            game_env_score = None
            td_upside_score = None
            rush_pct = None
            try:
                # Get pace metrics from pre-computed dictionaries
                team_plays = pace_data.get(team, 60.0)
                opp_plays = pace_data.get(opp, 60.0)
                game_plays = (team_plays + opp_plays) / 2
                
                team_pass_att = pass_att_data.get(team, 30.0)
                rush_pct = rush_pct_data.get(team, 50.0)
            
                # ITT from matchup
                team_itt = float(team_matchup.get("ITT", 20))
            
                # Normalize and weight components (0-100 scale)
                plays_score = ((game_plays - 48) / (62 - 48)) * 100
                pass_score = ((team_pass_att - 26) / (40 - 26)) * 100
                itt_score = ((team_itt - 13) / (32 - 13)) * 100
                epa_score = ((epa_adv) + 0.2) / 0.4 * 100
                ppd_score = ((ptd_adv) + 1.0) / 2.0 * 100
            
                # Weighted composite
                game_env_score = (
                    plays_score * 0.25 +
                    pass_score * 0.20 +
                    itt_score * 0.20 +
                    epa_score * 0.15 +
                    ppd_score * 0.20
                )
                game_env_score = max(0, min(100, game_env_score))
            
                # TD upside based on PPD advantage
                td_upside_score = ((ptd_adv) + 1.5) / 3.0 * 100
                td_upside_score = max(0, min(100, td_upside_score))
            
            except Exception:
                game_env_score = 50.0
                td_upside_score = 50.0
                rush_pct = 50.0
            
            # Pre-compute correlation data once per QB
            qb_wr_corr_wr = None
            qb_wr_corr_te = None
            qb_rb_corr = None
            if team_correlations is not None and not team_correlations.empty:
                team_corr_row = team_correlations[team_correlations['Team'] == team]
                if not team_corr_row.empty:
                    qb_wr_corr_wr = team_corr_row.iloc[0]['corr_qb_wr1']
                    qb_wr_corr_te = team_corr_row.iloc[0]['corr_qb_te1']
                    qb_rb_corr = team_corr_row.iloc[0].get('corr_qb_rb1', None)
            
            qb_dict = qb.to_dict()

            for combo in team_combos:

                stack_players = [qb_dict] + list(combo)
            
                # Handle bring-back logic
                stack_variations = []
                if "One Bringback" in stack_type:
                    # Generate multiple stack variations with different bring-backs for variety
                    for bringback in bringback_candidates:
                        stack_variations.append(stack_players + [bringback])
                else:
                    # No bring-back - single variation
                    stack_variations.append(stack_players)
            
                # Process each stack variation
                for stack_all in stack_variations:

                    total_proj = sum(p["dk"] for p in stack_all)
                    total_ceiling = sum(p["dk_ceiling"] for p in stack_all)
                    total_ceiling_adj = sum(p["ceiling_adj"] for p in stack_all)
                    total_salary = sum(p["salary"] for p in stack_all)
                    total_own = sum(p["dk_ownership"] for p in stack_all)

                    # Correlation-Adjusted Stack Boom Probability
                    stack_mean = sum(p["proj"] for p in stack_all)
                
                    # Calculate correlation-adjusted variance
                    stack_var = sum((p["stddev"] ** 2) for p in stack_all)
                
                    # Add covariance terms for correlated players
                    qb_idx = None
                    pass_catcher_indices = []
                
                    for i, p in enumerate(stack_all):
                        if p["position"] == "QB":
                            qb_idx = i
                        elif p["position"] in ["WR", "TE"]:
                            pass_catcher_indices.append(i)
                
                    # Add QB-receiver correlations
                    if qb_idx is not None:
                        qb_std = stack_all[qb_idx]["stddev"]
                        for pc_idx in pass_catcher_indices:
                            pc_std = stack_all[pc_idx]["stddev"]
                            # Only if both from same team (positive correlation)
                            if stack_all[qb_idx]["team"] == stack_all[pc_idx]["team"]:
                                stack_var += 2 * corr_qb_pass * qb_std * pc_std
                
                    # Add pass-catcher to pass-catcher correlations (same team)
                    for i in range(len(pass_catcher_indices)):
                        for j in range(i + 1, len(pass_catcher_indices)):
                            idx_i = pass_catcher_indices[i]
                            idx_j = pass_catcher_indices[j]
                            if stack_all[idx_i]["team"] == stack_all[idx_j]["team"]:
                                std_i = stack_all[idx_i]["stddev"]
                                std_j = stack_all[idx_j]["stddev"]
                                stack_var += 2 * corr_pass_pass * std_i * std_j
                
                    stack_std = math.sqrt(max(stack_var, 0))

                    # Boom target = sum of individual percentile-based boom targets
                    stack_boom_target = 0
                    for p in stack_all:
                        pos = p["position"]
                        sal = p["salary"]
                        stack_boom_target += get_boom_threshold(pos, sal)

                    stack_boom_prob = 1 - normal_cdf(stack_boom_target, stack_mean, stack_std)
                    stack_boom_prob = min(max(stack_boom_prob, 0), 1)

                    # New Stack Leverage = Boom% - Total_Own%
                    stack_leverage = (stack_boom_prob * 100) - (total_own * 100)

                    # Calculate stack value (projection per $1K salary)
                    stack_value = (total_proj / (total_salary / 1000)) if total_salary > 0 else 0
                
                    # Top Stack Score (Stokastic-inspired): probability of being highest-scoring stack
                    # Uses z-score of ceiling projection relative to field
                    # Higher ceiling + lower ownership = more likely to be top stack
                    # Store raw values for normalization after all stacks computed
                    top_stack_raw = total_ceiling_adj - (total_own * 50)  # Penalize high ownership
                
                    # Top Value Score: value efficiency normalized 0-100
                    top_value_raw = stack_value
                    
                    # Get correlation data for this stack
                    qb_wr_corr = None
                    stack_corr_label = "N/A"
                    stack_corr_rag = '⚪'
                    
                    if qb_wr_corr_wr is not None or qb_wr_corr_te is not None or qb_rb_corr is not None:
                        # Determine which correlation to show based on stack composition
                        positions_in_stack = [p['position'] for p in stack_all if p['position'] != 'QB']
                        if 'WR' in positions_in_stack:
                            qb_wr_corr = qb_wr_corr_wr
                        elif 'TE' in positions_in_stack:
                            qb_wr_corr = qb_wr_corr_te
                        elif 'RB' in positions_in_stack:
                            qb_wr_corr = qb_rb_corr
                        
                        if qb_wr_corr is not None and not pd.isna(qb_wr_corr):
                            stack_corr_label = get_correlation_label(qb_wr_corr)
                            stack_corr_rag = get_correlation_rag(qb_wr_corr)

                    results.append({
                        "QB": qb_dict["name"],
                        "Team": team,
                        "Opp": opp,
                        "Players": ", ".join([p["name"] for p in stack_all if p["position"] != "QB"]),
                        "Total_Proj": round(total_proj, 2),
                        "Total_Ceiling_Adj": round(total_ceiling_adj, 2),
                        "Ceiling_vs_Proj": round(total_ceiling - total_proj, 2),
                        "Ceil_Adj_vs_Proj": round(total_ceiling_adj - total_proj, 2),
                        "Stack_Value": round(stack_value, 2),
                        "Total_Salary": int(total_salary),
                        "Total_Own": round(total_own, 4),
                        "Total_Own%": round(total_own * 100, 1),
                        "Boom_Target": round(stack_boom_target, 1),
                        "Stack_Boom%": round(stack_boom_prob * 100, 1),
                        "Stack_Leverage": round(stack_leverage, 1),
                        "Game_Env_Score": round(game_env_score, 1) if game_env_score is not None else None,
                        "TD_Upside": round(td_upside_score, 1) if td_upside_score is not None else None,
                        "Rush_Pct": round(rush_pct, 1) if rush_pct is not None else None,
                        "QB_Corr": round(qb_wr_corr, 2) if qb_wr_corr is not None else None,
                        "Corr_Label": stack_corr_label,
                        "Corr_RAG": stack_corr_rag,
                        "Top_Stack_Raw": top_stack_raw,
                        "Top_Value_Raw": top_value_raw,
                        "EPA_Adv": epa_adv,
                        "YPP_Adv": ypp_adv,
                        "PTD_Adv": ptd_adv,
                        "EXP_Adv": exp_adv,
                        "DCR_Adv": dcr_adv,
                    })

        df_results = pd.DataFrame(results)
    
        # Normalize Top Stack and Top Value scores to 0-100 scale (Stokastic-inspired)
        if not df_results.empty and len(df_results) > 1:
            # Top Stack Score: z-score normalization then scale to 0-100
            top_stack_mean = df_results["Top_Stack_Raw"].mean()
            top_stack_std = df_results["Top_Stack_Raw"].std()
            if top_stack_std > 0:
                df_results["Top_Stack_z"] = (df_results["Top_Stack_Raw"] - top_stack_mean) / top_stack_std
                # Convert z-scores to 0-100 scale (z=-2 → 0, z=+2 → 100)
                df_results["Top_Stack_Score"] = ((df_results["Top_Stack_z"] + 2) / 4 * 100).clip(0, 100)
            else:
                df_results["Top_Stack_Score"] = 50.0
        
            # Top Value Score: normalize to 0-100
            value_min = df_results["Top_Value_Raw"].min()
            value_max = df_results["Top_Value_Raw"].max()
            if value_max > value_min:
                df_results["Top_Value_Score"] = ((df_results["Top_Value_Raw"] - value_min) / (value_max - value_min) * 100)
            else:
                df_results["Top_Value_Score"] = 50.0
        
            # Composite Stack Rating (Stokastic-inspired): 0-100 scale
            # Combines: Top Stack (35%), Top Value (25%), Boom% (25%), Low Ownership (15%)
            # Ownership inverted: lower ownership = higher score
            ownership_inverted = 100 - (df_results["Total_Own%"])
        
            df_results["Stack_Rating"] = (
                df_results["Top_Stack_Score"] * 0.35 +
                df_results["Top_Value_Score"] * 0.25 +
                df_results["Stack_Boom%"] * 0.25 +
                ownership_inverted * 0.15
            ).clip(0, 100)
        
            # Round display columns
            df_results["Top_Stack_Score"] = df_results["Top_Stack_Score"].round(1)
            df_results["Top_Value_Score"] = df_results["Top_Value_Score"].round(1)
            df_results["Stack_Rating"] = df_results["Stack_Rating"].round(1)
        
            # Drop temporary columns
            df_results = df_results.drop(columns=["Top_Stack_Raw", "Top_Value_Raw", "Top_Stack_z"], errors="ignore")
    
        # Limit to top 4 stacks per team (by Stack_Rating instead of Stack_Leverage)
        if not df_results.empty:
            df_results = (
                df_results
                .sort_values("Stack_Rating", ascending=False)
                .groupby("Team", as_index=False)
                .head(4)
            )
    
        return df_results



    # --------------------------------------------------------
    # 3. Player Boom/Bust View
    # --------------------------------------------------------
    if view_mode == "📊 Player Boom/Bust":
        st.subheader("📊 Player Boom/Bust Analysis")
        st.caption("Individual player boom/bust probabilities with historical performance data")
    
        # Player pool size targets for 20-lineup GPP
        pool_targets = DFSConfig.POOL_TARGETS = DFSConfig.POOL_TARGETS
    
        # Quick filter option - Row 1
        col_filter1, col_filter2, col_filter3, col_filter4 = st.columns([1, 1, 1.5, 1.5])
        with col_filter1:
            positions = sorted(df_filtered["position"].unique())
            pos_filter = st.selectbox("Position:", ["All"] + positions)
        with col_filter2:
            show_all = st.checkbox("📋 Show All", help="View all players without any filter constraints")
        with col_filter3:
            # Salary range filter
            min_salary = int(df_filtered["salary"].min())
            max_salary = int(df_filtered["salary"].max())
            salary_range = st.slider(
                "💰 Salary Range",
                min_value=min_salary,
                max_value=max_salary,
                value=(min_salary, max_salary),
                step=100,
                help="Filter players by salary range"
            )
        with col_filter4:
            # Ownership range filter
            min_own = 0.0
            max_own = float(df_filtered["dk_ownership"].max() * 100)
            own_range = st.slider(
                "👥 Ownership %",
                min_value=min_own,
                max_value=max_own,
                value=(min_own, max_own),
                step=0.5,
                help="Filter players by projected ownership percentage"
            )
        
        # Filter Row 2 - Leverage
        col_filter5, col_filter6, col_filter7 = st.columns([1.5, 1, 2.5])
        with col_filter5:
            # Leverage range filter
            min_lev = float(df_filtered["leverage_boom"].min() * 100)
            max_lev = float(df_filtered["leverage_boom"].max() * 100)
            lev_range = st.slider(
                "🎯 Leverage % (Boom - Own)",
                min_value=min_lev,
                max_value=max_lev,
                value=(min_lev, max_lev),
                step=0.5,
                help="Filter by leverage score (positive = underowned relative to upside)"
            )
        with col_filter6:
            leverage_sort = st.checkbox("📈 Sort by Leverage", value=False, help="Sort players by leverage score (highest first)")
        with col_filter7:
            st.caption("💡 **Leverage Guide**: >10% = High leverage | 5-10% = Medium | <5% = Low leverage")
        
        # Filter Row 3 - Game Script
        col_filter8, col_filter9 = st.columns([2, 2])
        with col_filter8:
            # Game script filter
            script_options = ["All"] + sorted(df_filtered["script_cat"].unique().tolist())
            script_filter = st.multiselect(
                "🎬 Game Script Filter",
                options=script_options,
                default=["All"],
                help="Filter by game environment: Shootout (high scoring), Blowout (lopsided), Competitive (close), Low-Scoring (defensive)"
            )
        with col_filter9:
            st.caption("💡 **Game Script Guide**: 🔥 Blowout(Fav) = Run-heavy | ⚡ Shootout = Pass volume | ⚖️ Competitive = Balanced | 🛡️ Low-Scoring = Defensive | ❄️ Blowout(Dog) = Garbage time")

        df_pos = df_filtered if pos_filter == "All" else df_filtered[df_filtered["position"] == pos_filter]
        
        # Apply salary filter
        df_pos = df_pos[(df_pos["salary"] >= salary_range[0]) & (df_pos["salary"] <= salary_range[1])]
        
        # Apply ownership filter
        df_pos = df_pos[(df_pos["dk_ownership"] * 100 >= own_range[0]) & (df_pos["dk_ownership"] * 100 <= own_range[1])]
        
        # Apply leverage filter
        df_pos = df_pos[(df_pos["leverage_boom"] * 100 >= lev_range[0]) & (df_pos["leverage_boom"] * 100 <= lev_range[1])]
        
        # Apply game script filter
        if "All" not in script_filter and len(script_filter) > 0:
            df_pos = df_pos[df_pos["script_cat"].isin(script_filter)]

        display_df = df_pos.copy()
    
        # Reset index to show row numbers starting from 1
        display_df = display_df.reset_index(drop=True)
        display_df.index = display_df.index + 1
        display_df.index.name = "#"
    
        display_df["Boom%"] = (display_df["boom_prob"] * 100).round(1)
        display_df["Bust%"] = (display_df["bust_prob"] * 100).round(1)
        display_df["Own%"] = (display_df["dk_ownership"] * 100).round(1)
        display_df["Lev (Boom-Own)%"] = (display_df["leverage_boom"] * 100).round(1)
        display_df["PROE"] = (display_df["proe"] * 100).round(1)  # Convert to percentage
        display_df["Salary"] = display_df["salary"]  # Keep raw value for color-coding
        display_df["Pts/$K"] = (display_df["ceiling_adj"] / (display_df["salary"] / 1000)).round(2)
        
        # Add Leverage Category column
        def leverage_category(lev):
            if lev >= 10:
                return "🔥 High"
            elif lev >= 5:
                return "⚡ Medium"
            elif lev >= 0:
                return "✓ Low"
            else:
                return "⚠️ Negative"
        
        display_df["Lev_Cat"] = display_df["Lev (Boom-Own)%"].apply(leverage_category)
        
        # Add game script columns
        display_df["Script_Cat"] = display_df["script_cat"]
        display_df["Blowout_Prob%"] = (display_df["blowout_prob"] * 100).round(1)
        display_df["Script_Impact"] = display_df["script_impact"].round(2)
    
        # Filter out players with 0% ownership
        display_df = display_df[display_df["dk_ownership"] > 0].copy()
        
        # Show leverage insights summary
        if len(display_df) > 0:
            high_lev = len(display_df[display_df["Lev (Boom-Own)%"] >= 10])
            med_lev = len(display_df[(display_df["Lev (Boom-Own)%"] >= 5) & (display_df["Lev (Boom-Own)%"] < 10)])
            low_lev = len(display_df[(display_df["Lev (Boom-Own)%"] >= 0) & (display_df["Lev (Boom-Own)%"] < 5)])
            neg_lev = len(display_df[display_df["Lev (Boom-Own)%"] < 0])
            
            col_lev1, col_lev2, col_lev3, col_lev4 = st.columns(4)
            with col_lev1:
                st.metric("🔥 High Leverage", f"{high_lev} players", "≥10%", help="Players with 10%+ leverage (boom% well above ownership)")
            with col_lev2:
                st.metric("⚡ Medium Leverage", f"{med_lev} players", "5-10%", help="Players with moderate leverage")
            with col_lev3:
                st.metric("✓ Low Leverage", f"{low_lev} players", "0-5%", help="Players with minimal leverage")
            with col_lev4:
                st.metric("⚠️ Negative Leverage", f"{neg_lev} players", "<0%", help="Players with higher ownership than boom probability")
    
        # --------------------------------------------------------
        # Calculate Normalized Player Ranking (0-100 scale)
        # --------------------------------------------------------
        def calculate_normalized_rank(row):
            """
            Comprehensive ranking combining multiple factors:
            - Leverage (Boom - Own): Measures tournament value
            - Boom%: High-ceiling upside potential
            - Ceiling (adjusted): Raw scoring potential
            - Bust% (inverted): Reliability/consistency
            - Pts/$K: Salary efficiency/value
        
            Returns: Normalized score 0-100 (higher = better)
            """
            # Component scores (normalize to 0-1 scale per position)
            leverage_score = max(0, min(1, (row["Lev (Boom-Own)%"] + 20) / 50))  # -20% to +30% → 0 to 1
            boom_score = row["Boom%"] / 100
            bust_score = 1 - (row["Bust%"] / 100)  # Invert: low bust = good
        
            # Ceiling and value scores (will be normalized per position)
            ceiling_raw = row["ceiling_adj"]
            value_raw = row["Pts/$K"]
        
            return {
                'leverage_score': leverage_score,
                'boom_score': boom_score,
                'bust_score': bust_score,
                'ceiling_raw': ceiling_raw,
                'value_raw': value_raw
            }
    
        # Calculate component scores
        rank_components = display_df.apply(calculate_normalized_rank, axis=1, result_type='expand')
        display_df = pd.concat([display_df, rank_components], axis=1)
    
        # Normalize ceiling and value per position (percentile-based)
        for pos in display_df["position"].unique():
            pos_mask = display_df["position"] == pos
            pos_data = display_df[pos_mask]
        
            if len(pos_data) > 1:
                # Percentile rank (0-1 scale)
                display_df.loc[pos_mask, 'ceiling_score'] = pos_data['ceiling_raw'].rank(pct=True)
                display_df.loc[pos_mask, 'value_score'] = pos_data['value_raw'].rank(pct=True)
            else:
                display_df.loc[pos_mask, 'ceiling_score'] = 0.5
                display_df.loc[pos_mask, 'value_score'] = 0.5
    
        # WR-specific bonus: High-variance, high-ceiling, low-owned plays (tournament winners)
        display_df['wr_variance_bonus'] = 0.0
        wr_mask = display_df["position"] == "WR"
        if wr_mask.any():
            wr_data = display_df[wr_mask]
            # High variance = high stddev_adj (top 50%)
            variance_threshold = wr_data["stddev_adj"].quantile(0.50)
            # High ceiling = top 50%
            ceiling_threshold = wr_data["ceiling_adj"].quantile(0.50)
        
            # Bonus criteria: high variance AND high ceiling AND <=10% owned
            bonus_mask = (
                wr_mask & 
                (display_df["stddev_adj"] >= variance_threshold) &
                (display_df["ceiling_adj"] >= ceiling_threshold) &
                (display_df["Own%"] <= 10)
            )
        
            # Add 10 point bonus (equivalent to 10% boost in ranking)
            display_df.loc[bonus_mask, 'wr_variance_bonus'] = 10.0
    
        # RB-specific bonus: Positive game script (home favorites with significant spread)
        display_df['rb_gamescript_bonus'] = 0.0
        rb_mask = display_df["position"] == "RB"
        if rb_mask.any():
            # Bonus criteria: RB + home game + favorite (negative spread) + significant margin (>3 points)
            # Negative spread means team is favored (e.g., -7 means 7-point favorite)
            gamescript_mask = (
                rb_mask & 
                (display_df["is_home"] == True) &
                (display_df["spread"] < -3)  # Favorite by more than 3 points
            )
        
            # Graduated bonus based on spread size (bigger favorite = more run volume expected)
            # -3 to -7: +5 points, -7 to -10: +8 points, >-10: +12 points
            moderate_fav = gamescript_mask & (display_df["spread"] >= -7)
            strong_fav = gamescript_mask & (display_df["spread"] < -7) & (display_df["spread"] >= -10)
            heavy_fav = gamescript_mask & (display_df["spread"] < -10)
        
            display_df.loc[moderate_fav, 'rb_gamescript_bonus'] = 5.0
            display_df.loc[strong_fav, 'rb_gamescript_bonus'] = 8.0
            display_df.loc[heavy_fav, 'rb_gamescript_bonus'] = 12.0
    
        # RB-specific bonus: High weighted opportunities (usage/volume)
        display_df['rb_volume_bonus'] = 0.0
        if rb_mask.any():
            # Weighted opportunities from Weekly_Stats (pre-calculated)
            # High volume = more opportunities for boom games
            # Graduated bonus: 18+ WO/G = +15, 15-17.9 = +10, 12-14.9 = +5
            elite_volume = rb_mask & (display_df["weighted_opp"] >= 18)
            high_volume = rb_mask & (display_df["weighted_opp"] >= 15) & (display_df["weighted_opp"] < 18)
            moderate_volume = rb_mask & (display_df["weighted_opp"] >= 12) & (display_df["weighted_opp"] < 15)
        
            display_df.loc[elite_volume, 'rb_volume_bonus'] = 15.0
            display_df.loc[high_volume, 'rb_volume_bonus'] = 10.0
            display_df.loc[moderate_volume, 'rb_volume_bonus'] = 5.0
    
        # QB-specific bonus: Favorable game environment + value pricing
        display_df['qb_gamescript_bonus'] = 0.0
        qb_mask = display_df["position"] == "QB"
        if qb_mask.any():
            # Base criteria for game script bonus
            home_bonus = display_df["is_home"] == True
            favorite_bonus = display_df["spread"] < 0  # Negative spread = favorite
            high_itt_bonus = display_df["implied_total"] >= 24  # High scoring expectation
            value_bonus = display_df["Salary"] < 8000  # Value pricing
        
            # Graduated bonus based on how many criteria are met
            # All 4 criteria: elite setup (+15 points)
            elite_setup = qb_mask & home_bonus & favorite_bonus & high_itt_bonus & value_bonus
            display_df.loc[elite_setup, 'qb_gamescript_bonus'] = 15.0
        
            # 3 criteria: strong setup (+10 points)
            # Check various 3-combo scenarios
            strong_setups = [
                qb_mask & home_bonus & favorite_bonus & high_itt_bonus & ~value_bonus,  # Not value
                qb_mask & home_bonus & favorite_bonus & ~high_itt_bonus & value_bonus,  # Lower ITT
                qb_mask & home_bonus & ~favorite_bonus & high_itt_bonus & value_bonus,  # Not favorite
                qb_mask & ~home_bonus & favorite_bonus & high_itt_bonus & value_bonus,  # Away
            ]
            for setup in strong_setups:
                display_df.loc[setup & (display_df['qb_gamescript_bonus'] == 0), 'qb_gamescript_bonus'] = 10.0
        
            # 2 criteria: decent setup (+5 points)
            # High ITT + Value is most important combo for GPP
            decent_setup = qb_mask & high_itt_bonus & value_bonus & (display_df['qb_gamescript_bonus'] == 0)
            display_df.loc[decent_setup, 'qb_gamescript_bonus'] = 5.0
    
        # PROE-based bonuses: Pass Rate Over Expected game environment impact
        # Positive PROE = pass-heavy (benefits QB/WR/pass-catching RB)
        # Negative PROE = run-heavy (benefits rushing RB/DST)
        display_df['proe_bonus'] = 0.0
    
        # QB/WR bonus: Positive PROE (pass-heavy game script)
        qb_wr_mask = display_df["position"].isin(["QB", "WR"])
        if qb_wr_mask.any():
            # Graduated bonus for positive PROE
            high_proe = qb_wr_mask & (display_df["proe"] >= 0.08)  # >8% over expected = elite pass environment
            moderate_proe = qb_wr_mask & (display_df["proe"] >= 0.04) & (display_df["proe"] < 0.08)  # 4-8% over
        
            display_df.loc[high_proe, 'proe_bonus'] = 12.0  # Elite pass game script
            display_df.loc[moderate_proe, 'proe_bonus'] = 6.0  # Moderate pass script
    
        # RB bonus: Context-dependent (pass-catching vs rushing)
        # Positive PROE = pass-catching RBs benefit
        # Negative PROE = rushing RBs benefit (more game script control)
        rb_mask = display_df["position"] == "RB"
        if rb_mask.any():
            # Pass-catching RBs in positive PROE (>4% over expected)
            # For now, apply modest bonus to all RBs in positive PROE as pass-catchers may benefit
            positive_proe_rb = rb_mask & (display_df["proe"] >= 0.04)
            display_df.loc[positive_proe_rb, 'proe_bonus'] = 3.0
        
            # Rushing RBs in negative PROE (run-heavy game script)
            negative_proe_rb = rb_mask & (display_df["proe"] <= -0.04)
            display_df.loc[negative_proe_rb, 'proe_bonus'] = 5.0
    
        # DST bonus: Negative PROE (opponent run-heavy = more predictable, easier to defend)
        dst_mask = display_df["position"].isin(["DST", "D"])
        if dst_mask.any():
            # Opponent's PROE would be ideal, but team PROE correlation is useful
            # Negative team PROE often correlates with positive game script (leading) = more sacks/turnovers
            negative_proe_dst = dst_mask & (display_df["proe"] <= -0.04)
            display_df.loc[negative_proe_dst, 'proe_bonus'] = 4.0
    
        # Weighted composite ranking
        # Leverage = most important (40%), Boom = 25%, Ceiling = 15%, Value = 10%, Bust = 10%
        # + WR variance bonus for GPP upside plays
        # + RB game script bonus for favorable game environments
        # + RB volume bonus for high weighted opportunities
        # + QB game script bonus for scoring environment + value pricing
        # + PROE bonus for pass/run environment fit
        display_df['Player_Rank'] = (
            display_df['leverage_score'] * 40 +
            display_df['boom_score'] * 25 +
            display_df['ceiling_score'] * 15 +
            display_df['value_score'] * 10 +
            display_df['bust_score'] * 10 +
            display_df['wr_variance_bonus'] +
            display_df['rb_gamescript_bonus'] +
            display_df['rb_volume_bonus'] +
            display_df['qb_gamescript_bonus'] +
            display_df['proe_bonus']
        ).round(1)
    
        # Clean up temporary columns
        display_df = display_df.drop(columns=['leverage_score', 'boom_score', 'bust_score', 
                                              'ceiling_raw', 'value_raw', 'ceiling_score', 'value_score', 
                                              'wr_variance_bonus', 'rb_gamescript_bonus', 'rb_volume_bonus', 'qb_gamescript_bonus', 'proe_bonus'])
        
        # Sort by leverage if checkbox is enabled
        if leverage_sort:
            display_df = display_df.sort_values(by="Lev (Boom-Own)%", ascending=False)

        cols = [
            "name", "team", "opponent", "position", "Salary", "Pts/$K",
            "proj_adj", "stddev_adj", "ceiling_adj", "max_dk", "avg_dk", "floor_25", "ceil_75",
            "Boom%", "Bust%", "Own%", "Lev (Boom-Own)%", "Lev_Cat", 
            "Script_Cat", "Blowout_Prob%", "Script_Impact",
            "PROE", "Player_Rank", "hits_4x"
        ]

        # --------------------------------------------------------
        # Dynamic RAG scaling based on filtered dataset (display_df)
        # Recalculate quantiles for the current filtered view
        # --------------------------------------------------------
        def rag_relative(df, col, reverse=False):
            """
            reverse=False → high = green (Boom%, Leverage)
            reverse=True  → low = green (Bust%, Own%)
            
            Quantiles are calculated dynamically based on the filtered dataframe
            to ensure RAG colors reflect relative performance within the current view.
            """
            # Recalculate quantiles based on filtered data
            p33 = df[col].quantile(0.33)
            p66 = df[col].quantile(0.66)

            def color_func(val):
                if pd.isna(val):
                    return ""
                if reverse:
                    # lower = better (green)
                    if val <= p33:
                        return "background-color: #2ECC71; color: black;"
                    elif val <= p66:
                        return "background-color: #F1C40F; color: black;"
                    else:
                        return "background-color: #E74C3C; color: white;"
                else:
                    # higher = better (green)
                    if val >= p66:
                        return "background-color: #2ECC71; color: black;"
                    elif val >= p33:
                        return "background-color: #F1C40F; color: black;"
                    else:
                        return "background-color: #E74C3C; color: white;"

            return color_func

        # Fixed ownership color function (not relative to dataset)
        def ownership_color(val):
            """Fixed thresholds for ownership: <=10% green, 10-20% amber, >=20% red"""
            if pd.isna(val):
                return ""
            if val <= 10:
                return "background-color: #2ECC71; color: black;"
            elif val < 20:
                return "background-color: #F1C40F; color: black;"
            else:
                return "background-color: #E74C3C; color: white;"
    
        # PROE color function (positive = pass-heavy, negative = run-heavy)
        def proe_color(val):
            """Color PROE: Positive (green) = pass-heavy, Negative (amber/red) = run-heavy, Near zero (yellow)"""
            if pd.isna(val):
                return ""
            if val >= 8.0:  # >8% over expected = elite pass environment
                return "background-color: #27AE60; color: white;"  # Dark green
            elif val >= 4.0:  # 4-8% over = moderate pass environment
                return "background-color: #2ECC71; color: black;"  # Green
            elif val >= -4.0:  # -4% to 4% = neutral
                return "background-color: #F1C40F; color: black;"  # Yellow
            elif val >= -8.0:  # -8% to -4% = moderate run environment
                return "background-color: #E67E22; color: white;"  # Orange
            else:  # <-8% = heavy run environment
                return "background-color: #E74C3C; color: white;"  # Red
        
        # Leverage category color function
        def lev_cat_color(val):
            """Color leverage categories: High = green, Medium = yellow, Low = amber, Negative = red"""
            if pd.isna(val) or val == "":
                return ""
            if "High" in str(val):
                return "background-color: #27AE60; color: white; font-weight: bold;"  # Dark green
            elif "Medium" in str(val):
                return "background-color: #F1C40F; color: black;"  # Yellow
            elif "Low" in str(val):
                return "background-color: #E67E22; color: white;"  # Orange
            else:  # Negative
                return "background-color: #E74C3C; color: white;"  # Red
        
        # Game script category color function
        def script_cat_color(val):
            """Color game script categories: Shootout/Blowout(Fav) = green, Competitive = yellow, Low-Scoring/Blowout(Dog) = amber"""
            if pd.isna(val) or val == "":
                return ""
            if "Shootout" in str(val):
                return "background-color: #8E44AD; color: white; font-weight: bold;"  # Purple (high scoring)
            elif "Blowout (Fav)" in str(val):
                return "background-color: #27AE60; color: white; font-weight: bold;"  # Dark green
            elif "Blowout (Dog)" in str(val):
                return "background-color: #3498DB; color: white;"  # Blue
            elif "Competitive" in str(val):
                return "background-color: #F1C40F; color: black;"  # Yellow
            else:  # Low-Scoring
                return "background-color: #95A5A6; color: white;"  # Gray
        
        # Script impact color function (multiplier)
        def script_impact_color(val):
            """Color script impact: >1.10 = green, 1.05-1.10 = light green, 0.95-1.05 = yellow, <0.95 = red"""
            if pd.isna(val):
                return ""
            if val >= 1.10:
                return "background-color: #27AE60; color: white; font-weight: bold;"  # Dark green
            elif val >= 1.05:
                return "background-color: #2ECC71; color: black;"  # Green
            elif val >= 0.95:
                return "background-color: #F1C40F; color: black;"  # Yellow
            elif val >= 0.85:
                return "background-color: #E67E22; color: white;"  # Orange
            else:
                return "background-color: #E74C3C; color: white;"  # Red
    
        styled = (
            display_df[cols]
            .style
            .format("{:.1f}", subset=["proj_adj", "stddev_adj", "ceiling_adj", "max_dk", "avg_dk", "floor_25", "ceil_75", "Player_Rank", "PROE", "Blowout_Prob%"])
            .format("{:.2f}", subset=["Pts/$K", "Script_Impact"])
            .format("{:.1f}", subset=["Boom%", "Bust%", "Own%", "Lev (Boom-Own)%"])
            .format("{:.0f}", subset=["hits_4x"])
            .format("${:,.0f}", subset=["Salary"])  # Currency format for salary
            .map(rag_relative(display_df, "Pts/$K"), subset=["Pts/$K"])  # Higher value = better
            .map(rag_relative(display_df, "Salary", reverse=True), subset=["Salary"])  # Lower salary = better value
            .map(rag_relative(display_df, "ceiling_adj"), subset=["ceiling_adj"])  # Higher ceiling = better
            .map(rag_relative(display_df, "Boom%"), subset=["Boom%"])
            .map(rag_relative(display_df, "Bust%", reverse=True), subset=["Bust%"])
            .map(ownership_color, subset=["Own%"])  # Fixed thresholds for ownership
            .map(rag_relative(display_df, "Lev (Boom-Own)%"), subset=["Lev (Boom-Own)%"])
            .map(lev_cat_color, subset=["Lev_Cat"])  # Leverage category colors
            .map(script_cat_color, subset=["Script_Cat"])  # Game script category colors
            .map(rag_relative(display_df, "Blowout_Prob%"), subset=["Blowout_Prob%"])  # Higher blowout prob = red (volatile)
            .map(script_impact_color, subset=["Script_Impact"])  # Script impact multiplier colors
            .map(proe_color, subset=["PROE"])  # PROE-specific color scheme
            .map(rag_relative(display_df, "Player_Rank"), subset=["Player_Rank"])  # Higher rank = better
            .map(rag_relative(display_df, "hits_4x"), subset=["hits_4x"])
        )

        st.dataframe(styled, width="stretch")

        st.download_button(
            "📥 Download Player Boom/Bust CSV",
            data=display_df[cols].to_csv(index=False),
            file_name="player_boom_bust.csv",
            mime="text/csv",
            key="download_boom_bust"
        )



    # --------------------------------------------------------
    # 4. Top Stacks View
    # --------------------------------------------------------
    if view_mode == "🧱 Top Stacks":
        st.subheader("🧱 Top Stacks (Matchup-Aware)")
        st.caption("Generate and rank QB stacks with teammates and optional bringbacks")
    
        # Position selection row
        with st.expander("⚙️ Stack Position Settings", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                stack_positions = st.multiselect(
                    "Stack Positions (QB Teammates):",
                    ["WR", "TE", "RB"],
                    default=["WR", "TE"],
                    help="Select which positions to include when stacking with QB"
                )
            with col_b:
                bringback_positions = st.multiselect(
                    "Bring-Back Positions (Opponents):",
                    ["WR", "TE", "RB"],
                    default=["WR", "TE", "RB"],
                    help="Select which opponent positions to consider for bring-backs"
                )
        
            if not stack_positions:
                st.warning("⚠️ Please select at least one stack position")
            if not bringback_positions:
                st.info("ℹ️ No bring-back positions selected - 'One Bringback' stacks will be unavailable")
    
        # Control row with 3 columns
        col1, col2, col3 = st.columns([2, 1, 2])
    
        with col1:
            stack_option = st.selectbox(
                "Stack Configuration:",
                [
                    "QB+1, No Bringback",
                    "QB+1, One Bringback",
                    "QB+2, No Bringback",
                    "QB+2, One Bringback",
                    "QB+3, No Bringback",
                    "QB+3, One Bringback",
                ],
                help="QB+N = QB with N teammates (WR/TE). Bringback = opponent skill player"
            )
    
        with col2:
            top_n_choice = st.selectbox(
                "Show Top:",
                ["10", "25", "50", "100", "All"],
                index=1,
                help="Number of stacks to display"
            )
            top_n = None if top_n_choice == "All" else int(top_n_choice)
    
        with col3:
            rank_metric = st.selectbox(
                "Rank By:",
                [
                    "Stack_Rating",
                    "Top_Stack_Score",
                    "Top_Value_Score",
                    "Stack_Value",
                    "Game_Env_Score",
                    "Stack_Leverage",
                    "Stack_Boom%",
                    "Total_Ceiling_Adj",
                    "Ceil_Adj_vs_Proj",
                    "EPA_Adv",
                    "Total_Proj",
                    "YPP_Adv",
                    "PTD_Adv",
                    "EXP_Adv",
                    "DCR_Adv",
                    "Ceiling_vs_Proj",
                    "Rush_Pct (Asc)",
                    "Total_Salary (Asc)",
                    "Total_Own (Asc)",
                ],
                help="Metric to sort stacks by (green = good, red = bad in table)"
            )

        if df_filtered.empty:
            st.warning("⚠️ No players match the current filters. Try adjusting the sidebar filters.")
        elif not stack_positions:
            st.warning("⚠️ Please select at least one stack position to generate stacks")
        else:
            # Add progress indicator with detailed status
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
        
            try:
                progress_placeholder.text("🔄 Analyzing player pool...")
                progress_bar.progress(0.2)
            
                progress_placeholder.text("🔄 Generating stack combinations...")
                progress_bar.progress(0.4)
            
                stack_df = get_stack(df_filtered, matchup_dict, stack_option, stack_positions, bringback_positions)
            
                progress_placeholder.text("✅ Stack generation complete!")
                progress_bar.progress(1.0)
            
                # Clear progress indicators after brief delay
                import time
                time.sleep(0.5)
                progress_placeholder.empty()
                progress_bar.empty()
            
            except Exception as e:
                progress_placeholder.empty()
                progress_bar.empty()
                st.error(f"❌ Error generating stacks: {e}")
                st.stop()

            if stack_df.empty:
                st.warning("⚠️ No stacks generated. Try different filters or stack configuration.")
            else:
                # Display total stacks generated
                total_stacks = len(stack_df)
                st.info(f"📊 Generated {total_stacks} total stacks from filtered players")
            
                # Metrics legend
                with st.expander("📖 Metric Definitions", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("""
                        **Core Metrics:**
                        - **Stack_Rating**: 0-100 composite score (Top Stack 35%, Top Value 25%, Boom% 25%, Low Own 15%)
                        - **Top_Stack_Score**: 0-100 probability this stack will be highest-scoring of the week
                        - **Top_Value_Score**: 0-100 normalized value efficiency (projection per $1K)
                        - **Stack_Value**: Projection per $1K salary (value play identifier)
                        - **Boom_Target**: DK points threshold for boom (95th percentile, calibrated to 230+ winning lineups)
                        - **Stack_Boom%**: Probability stack exceeds boom threshold
                        - **Stack_Leverage**: Boom% minus Ownership% (positive = leverage)
                        - **QB_Corr**: QB ↔ Receiver correlation (-1 to 1, historical performance)
                          - 🟢 **≥0.4**: Strong positive (spike together - ideal for stacking)
                          - 🟡 **0.2-0.4**: Moderate positive
                          - ⚪ **-0.2 to 0.2**: Weak/Independent
                          - 🔴 **<-0.2**: Negative (cannibalize - avoid stacking)
                        - **Game_Env_Score**: 0-100 composite (pace + volume + ITT + EPA + TD rate)
                        - **TD_Upside**: 0-100 score comparing offense TD rate vs defense TD allowed
                        - **Rush_Pct**: Rush play percentage (lower = more pass volume)
                        - **Total_Ceiling_Adj**: Matchup-adjusted ceiling sum
                        """)
                    with col2:
                        st.markdown("""
                        **Matchup Metrics (Advantage = Team Offense vs Opp Defense):**
                        - **EPA_Adv**: Expected Points Added advantage
                        - **YPP_Adv**: Yards Per Play advantage
                        - **PTD_Adv**: Points Per Drive advantage
                        - **EXP/DCR_Adv**: Explosive Play / Down Conversion Rate
                    
                        💡 **Stack_Rating** is the best overall metric (like Stokastic's rating)
                        💡 **Top_Stack_Score** shows probability of being #1 stack of the week
                        💡 Lower **Rush_Pct** = more passing opportunities
                        """)

                # Sorting
                if rank_metric == "Total_Salary (Asc)":
                    stack_df = stack_df.sort_values("Total_Salary", ascending=True)
                elif rank_metric == "Total_Own (Asc)":
                    stack_df = stack_df.sort_values("Total_Own", ascending=True)
                elif rank_metric == "Rush_Pct (Asc)":
                    stack_df = stack_df.sort_values("Rush_Pct", ascending=True)
                else:
                    stack_df = stack_df.sort_values(rank_metric, ascending=False)

                # Limit
                if top_n is not None:
                    stack_df = stack_df.head(top_n)
            
                # Reset index to show rank order (1, 2, 3, ...)
                stack_df = stack_df.reset_index(drop=True)
                stack_df.index = stack_df.index + 1  # Start from 1 instead of 0
                stack_df.index.name = "Rank"

                # Prepare display dataframe
                display_cols = [
                    "QB", "Team", "Opp", "Players",
                    "Stack_Rating", "Top_Stack_Score", "Top_Value_Score",
                    "Total_Proj", "Total_Ceiling_Adj", "Ceiling_vs_Proj", "Ceil_Adj_vs_Proj",
                    "Stack_Value", "Total_Salary", "Total_Own%", "Boom_Target", "Stack_Boom%", "Stack_Leverage",
                    "QB_Corr", "Corr_Label",
                    "Game_Env_Score", "TD_Upside", "Rush_Pct", "EPA_Adv", "YPP_Adv", "PTD_Adv", "EXP_Adv", "DCR_Adv"
                ]
            
                # RAG color function for stacks
                def stack_rag(df, col, reverse=False):
                    """RAG coloring based on quantiles"""
                    p33 = df[col].quantile(0.33)
                    p66 = df[col].quantile(0.66)
                
                    def color_func(val):
                        if pd.isna(val):
                            return ""
                        if reverse:
                            if val <= p33:
                                return "background-color: #2ECC71; color: black;"
                            elif val <= p66:
                                return "background-color: #F1C40F; color: black;"
                            else:
                                return "background-color: #E74C3C; color: white;"
                        else:
                            if val >= p66:
                                return "background-color: #2ECC71; color: black;"
                            elif val >= p33:
                                return "background-color: #F1C40F; color: black;"
                            else:
                                return "background-color: #E74C3C; color: white;"
                    return color_func
            
                # Create a helper column for styling (will be removed from display)
                display_df = stack_df[display_cols].copy()
                
                # Convert None values to NaN for proper formatting
                display_df = display_df.fillna(value=pd.NA)
            
                # Color function for Boom_Target
                def color_boom_target(row):
                    styles = [''] * len(row)
                    boom_idx = display_df.columns.get_loc("Boom_Target")
                    if row["Boom_Target"] > row["Total_Ceiling_Adj"]:
                        styles[boom_idx] = 'background-color: #E74C3C; color: white;'
                    else:
                        styles[boom_idx] = 'background-color: #2ECC71; color: black;'
                    return styles
                
                # Color function for correlation
                def corr_color(val):
                    if pd.isna(val) or val is None:
                        return ""
                    if val >= 0.4:
                        return "background-color: #2ECC71; color: black;"  # Strong positive
                    elif val >= 0.2:
                        return "background-color: #F1C40F; color: black;"  # Moderate positive
                    elif val >= -0.2:
                        return "background-color: #F8F9FA; color: black;"  # Neutral
                    else:
                        return "background-color: #E74C3C; color: white;"  # Negative
            
                # Apply styling
                styled_stacks = (
                    display_df.style
                    .format("{:.1f}", subset=["Stack_Rating", "Top_Stack_Score", "Top_Value_Score",
                                               "Total_Proj", "Total_Ceiling_Adj", "Ceiling_vs_Proj", "Ceil_Adj_vs_Proj",
                                               "Boom_Target", "Stack_Boom%", "Stack_Leverage", "Game_Env_Score", "TD_Upside", "Rush_Pct"])
                    .format("{:.2f}", subset=["Stack_Value", "QB_Corr", "EPA_Adv", "YPP_Adv", "PTD_Adv", "EXP_Adv", "DCR_Adv"])
                    .format("{:.1f}", subset=["Total_Own%"])
                    .format("${:,.0f}", subset=["Total_Salary"])
                    .apply(color_boom_target, axis=1)
                    .map(stack_rag(stack_df, "Stack_Rating"), subset=["Stack_Rating"])
                    .map(stack_rag(stack_df, "Top_Stack_Score"), subset=["Top_Stack_Score"])
                    .map(stack_rag(stack_df, "Top_Value_Score"), subset=["Top_Value_Score"])
                    .map(stack_rag(stack_df, "Stack_Value"), subset=["Stack_Value"])
                    .map(stack_rag(stack_df, "Total_Ceiling_Adj"), subset=["Total_Ceiling_Adj"])
                    .map(stack_rag(stack_df, "Ceil_Adj_vs_Proj"), subset=["Ceil_Adj_vs_Proj"])
                    .map(corr_color, subset=["QB_Corr"])
                    .map(stack_rag(stack_df, "Stack_Boom%"), subset=["Stack_Boom%"])
                    .map(stack_rag(stack_df, "Stack_Leverage"), subset=["Stack_Leverage"])
                    .map(stack_rag(stack_df, "Game_Env_Score"), subset=["Game_Env_Score"])
                    .map(stack_rag(stack_df, "TD_Upside"), subset=["TD_Upside"])
                    .map(stack_rag(stack_df, "Rush_Pct", reverse=True), subset=["Rush_Pct"])
                    .map(stack_rag(stack_df, "Total_Own%", reverse=True), subset=["Total_Own%"])
                    .map(stack_rag(stack_df, "EPA_Adv"), subset=["EPA_Adv"])
                    .map(stack_rag(stack_df, "Total_Salary", reverse=True), subset=["Total_Salary"])
                )

                st.dataframe(styled_stacks, width='stretch', column_config={
                    "QB": st.column_config.Column(pinned=True),
                    "Team": st.column_config.Column(pinned=True),
                    "Opp": st.column_config.Column(pinned=True),
                    "Players": st.column_config.Column(pinned=True),
                    "Stack_Rating": st.column_config.Column(pinned=True),
                    "Top_Stack_Score": st.column_config.Column(pinned=True),
                })

                st.download_button(
                    "📥 Download Stacks CSV",
                    data=stack_df.to_csv(index=False),
                    file_name=f"top_stacks_{stack_option.replace(' ', '_')}.csv",
                    mime="text/csv",
                    key=f"download_stacks_{stack_option.replace(' ', '_')}"
                )


    # --------------------------------------------------------
    # 5. Game Matchup Analysis View
    # --------------------------------------------------------
    if view_mode == "⚔️ Game Matchups":
        st.subheader("⚔️ Game Matchup Analysis")
        st.caption("Comprehensive team-level metrics using Sharp Football stats, Vegas lines, and PROE data")
    
        # Get list of teams that are actually on the main slate (from players data)
        main_slate_teams = set(df["team"].unique())
    
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
    
        # Load PROE data for current week
        try:
            data_dir = Path(DFSConfig.DATA_DIR)
            weekly_proe = pd.read_csv(data_dir / "weekly_proe_2025.csv")
            current_week_proe = weekly_proe[weekly_proe["week"] == weekly_proe["week"].max()].copy()
            proe_dict = current_week_proe.set_index("posteam")["proe"].to_dict()
        except:
            proe_dict = {}
    
        # Calculate team-level pace metrics from Weekly_Stats.csv
        try:
            weekly_stats = pd.read_csv(data_dir / "Weekly_Stats.csv")
            # Get recent weeks for pace calculation (last 4-6 weeks)
            recent_weeks = weekly_stats["Week"].max()
            lookback = 4
            recent_stats = weekly_stats[weekly_stats["Week"] > (recent_weeks - lookback)].copy()
        
            # Aggregate team-level metrics
            team_pace = recent_stats.groupby("Team").agg({
                "Pass_Att": "sum",
                "Rush_Att": "sum"
            }).reset_index()
        
            # Calculate plays per game and pass rate
            team_pace["Total_Plays"] = team_pace["Pass_Att"] + team_pace["Rush_Att"]
            team_pace["Plays_Per_Game"] = (team_pace["Total_Plays"] / lookback).round(1)
            team_pace["Pass_Rate"] = (team_pace["Pass_Att"] / team_pace["Total_Plays"] * 100).round(1)
        
            # Create dictionaries for lookups
            plays_per_game_dict = team_pace.set_index("Team")["Plays_Per_Game"].to_dict()
            pass_rate_dict = team_pace.set_index("Team")["Pass_Rate"].to_dict()
        except Exception as e:
            st.warning(f"⚠️ Could not load team pace metrics: {e}")
            plays_per_game_dict = {}
            pass_rate_dict = {}
    
        # Build game matchup dataframe
        matchup_data = []
        processed_games = set()  # Track games we've already added
    
        for _, row in matchups.iterrows():
            init_team = row["Init"]
            opp_team = row["Opp"]
        
            # Skip if neither team is on the main slate (island games)
            if init_team not in main_slate_teams or opp_team not in main_slate_teams:
                continue
        
            # Create a unique game identifier (sorted teams to catch both directions)
            game_id = tuple(sorted([init_team, opp_team]))
        
            # Skip if we've already processed this game
            if game_id in processed_games:
                continue
            processed_games.add(game_id)
        
            # Convert abbreviations to full names for Sharp Football lookups
            init_full_name = abbrev_to_full.get(init_team, init_team)
            opp_full_name = abbrev_to_full.get(opp_team, opp_team)
        
            # Get team offensive stats (Sharp Football)
            init_off = team_offense_dict.get(init_full_name, {})
            opp_off = team_offense_dict.get(opp_full_name, {})
        
            # Get team defensive stats (Sharp Football)
            init_def = team_defense_dict.get(init_full_name, {})
            opp_def = team_defense_dict.get(opp_full_name, {})
        
            # Get game context from matchup file
            init_matchup = matchup_expanded.get(init_team, {})
            opp_matchup = matchup_expanded.get(opp_team, {})
        
            # Extract Sharp Football metrics
            init_epa = float(init_off.get("EPA_Play", 0))
            init_ypp = float(init_off.get("Yards Per Play", 0))
            init_ppd = float(init_off.get("Points Per Drive", 0))
            init_explosive = float(init_off.get("Explosive Play Rate", 0))
            init_dcr = float(init_off.get("Down Conversion Rate", 0))
        
            opp_epa = float(opp_off.get("EPA_Play", 0))
            opp_ypp = float(opp_off.get("Yards Per Play", 0))
            opp_ppd = float(opp_off.get("Points Per Drive", 0))
            opp_explosive = float(opp_off.get("Explosive Play Rate", 0))
            opp_dcr = float(opp_off.get("Down Conversion Rate", 0))
        
            # Defensive metrics
            init_def_epa = float(init_def.get("EPA_Play_Allowed", 0))
            init_def_ypp = float(init_def.get("Yards Per Play Allowed", 0))
            init_def_ppd = float(init_def.get("Points Per Drive Allowed", 0))
            init_def_explosive = float(init_def.get("Explosive Play Rate Allowed", 0))
            init_def_dcr = float(init_def.get("Down Conversion Rate Allowed", 0))
        
            opp_def_epa = float(opp_def.get("EPA_Play_Allowed", 0))
            opp_def_ypp = float(opp_def.get("Yards Per Play Allowed", 0))
            opp_def_ppd = float(opp_def.get("Points Per Drive Allowed", 0))
            opp_def_explosive = float(opp_def.get("Explosive Play Rate Allowed", 0))
            opp_def_dcr = float(opp_def.get("Down Conversion Rate Allowed", 0))
        
            # Vegas lines
            init_itt = float(init_matchup.get("ITT", 0))
            init_spread = float(init_matchup.get("Spread", 0))
            game_total = float(init_matchup.get("Total", 0))
        
            opp_itt = float(opp_matchup.get("ITT", 0))  # Each team has their own ITT value
            opp_spread = float(opp_matchup.get("Spread", 0))  # Each team has their own spread value
        
            # PROE data
            init_proe = proe_dict.get(init_team, 0) * 100  # Convert to percentage
            opp_proe = proe_dict.get(opp_team, 0) * 100
        
            # Team pace metrics from Weekly_Stats
            init_plays_pg = plays_per_game_dict.get(init_team, 0)
            opp_plays_pg = plays_per_game_dict.get(opp_team, 0)
            game_pace = round((init_plays_pg + opp_plays_pg) / 2, 1) if init_plays_pg and opp_plays_pg else 0
        
            init_pass_rate = pass_rate_dict.get(init_team, 0)
            opp_pass_rate = pass_rate_dict.get(opp_team, 0)
        
            # Calculate matchup advantages (Team Offense vs Opponent Defense)
            # Positive = offensive advantage, Negative = defensive disadvantage
            init_epa_adv = init_epa - opp_def_epa
            init_ypp_adv = init_ypp - opp_def_ypp
            init_ppd_adv = init_ppd - opp_def_ppd
            init_explosive_adv = init_explosive - opp_def_explosive
            init_dcr_adv = init_dcr - opp_def_dcr
        
            opp_epa_adv = opp_epa - init_def_epa
            opp_ypp_adv = opp_ypp - init_def_ypp
            opp_ppd_adv = opp_ppd - init_def_ppd
            opp_explosive_adv = opp_explosive - init_def_explosive
            opp_dcr_adv = opp_dcr - init_def_dcr
            

            matchup_data.append({
                "Game": f"{init_team} @ {opp_team}",
                "Team": init_team,
                "Opp": opp_team,
                "Total": game_total,
                "ITT": init_itt,
                "Spread": init_spread,
                "Pace": game_pace,
                "Pass%": init_pass_rate,
                "PROE": round(init_proe, 1),
                "EPA_Adv": round(init_epa_adv, 3),
                "YPP_Adv": round(init_ypp_adv, 2),
                "PPD_Adv": round(init_ppd_adv, 2),
                "Explosive_Adv": round(init_explosive_adv, 1),
                "DCR_Adv": round(init_dcr_adv, 1),
            })
        
            matchup_data.append({
                "Game": f"{init_team} @ {opp_team}",
                "Team": opp_team,
                "Opp": init_team,
                "Total": game_total,
                "ITT": opp_itt,
                "Spread": opp_spread,
                "Pace": game_pace,
                "Pass%": opp_pass_rate,
                "PROE": round(opp_proe, 1),
                "EPA_Adv": round(opp_epa_adv, 3),
                "YPP_Adv": round(opp_ypp_adv, 2),
                "PPD_Adv": round(opp_ppd_adv, 2),
                "Explosive_Adv": round(opp_explosive_adv, 1),
                "DCR_Adv": round(opp_dcr_adv, 1),
            })
    
        matchup_df = pd.DataFrame(matchup_data)
    
        if not matchup_df.empty:
            # Sort by Game Total and Pace (highest scoring, fastest games at top)
            matchup_df = matchup_df.sort_values(["Total", "Pace"], ascending=[False, False])
        
            # Reset index
            matchup_df = matchup_df.reset_index(drop=True)
            matchup_df.index = matchup_df.index + 1
            matchup_df.index.name = "#"
        
            # Metric legend
            with st.expander("📖 Metric Definitions", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    **Vegas & Game Environment:**
                    - **Total**: Game total (combined points expected)
                    - **ITT**: Implied Team Total (team's scoring expectation)
                    - **Spread**: Point spread (negative = favorite)
                    - **Pace**: Combined plays per game (avg of both teams)
                    - **Pass%**: Team's pass rate (% of plays that are passes)
                    - **PROE**: Pass Rate Over Expected (>0 = pass-heavy, <0 = run-heavy)
                
                    **Matchup Advantages (Offense vs Opponent Defense):**
                    All advantage metrics compare team's offense to opponent's defense
                    - **Positive values** = Offensive advantage (team offense > opponent defense)
                    - **Negative values** = Defensive advantage (opponent defense > team offense)
                    """)
                with col2:
                    st.markdown("""
                    **Sharp Football Advantage Metrics:**
                    - **EPA_Adv**: EPA advantage (Team EPA - Opp EPA Allowed)
                    - **YPP_Adv**: Yards per play advantage
                    - **PPD_Adv**: Points per drive advantage
                    - **Explosive_Adv**: Explosive play rate advantage
                    - **DCR_Adv**: Down conversion rate advantage
                
                    💡 **Green** = Positive advantage | **Yellow** = Neutral | **Red** = Disadvantage
                
                    **Strategy**: Target high Total + high Pace games with positive EPA/PPD advantages
                    """)
        
            # RAG coloring function
            def matchup_rag(df, col, reverse=False):
                p33 = df[col].quantile(0.33)
                p66 = df[col].quantile(0.66)
            
                def color_func(val):
                    if pd.isna(val):
                        return ""
                    if reverse:
                        if val <= p33:
                            return "background-color: #2ECC71; color: black;"
                        elif val <= p66:
                            return "background-color: #F1C40F; color: black;"
                        else:
                            return "background-color: #E74C3C; color: white;"
                    else:
                        if val >= p66:
                            return "background-color: #2ECC71; color: black;"
                        elif val >= p33:
                            return "background-color: #F1C40F; color: black;"
                        else:
                            return "background-color: #E74C3C; color: white;"
                return color_func
        
            # PROE color function
            def proe_color(val):
                if pd.isna(val):
                    return ""
                if val >= 8.0:
                    return "background-color: #27AE60; color: white;"
                elif val >= 4.0:
                    return "background-color: #2ECC71; color: black;"
                elif val >= -4.0:
                    return "background-color: #F1C40F; color: black;"
                elif val >= -8.0:
                    return "background-color: #E67E22; color: white;"
                else:
                    return "background-color: #E74C3C; color: white;"
        
            # Spread color function (negative = favorite)
            def spread_color(val):
                if pd.isna(val):
                    return ""
                if val <= -7:
                    return "background-color: #27AE60; color: white;"  # Big favorite
                elif val <= -3:
                    return "background-color: #2ECC71; color: black;"  # Moderate favorite
                elif val <= 3:
                    return "background-color: #F1C40F; color: black;"  # Pick'em
                elif val <= 7:
                    return "background-color: #E67E22; color: white;"  # Moderate underdog
                else:
                    return "background-color: #E74C3C; color: white;"  # Big underdog
        
            # Apply styling
            styled_matchups = (
                matchup_df
                .style
                .format("{:.1f}", subset=["Total", "ITT", "Pace", "Pass%", "PROE", "Explosive_Adv", "DCR_Adv"])
                .format("{:.1f}", subset=["Spread"])
                .format("{:.3f}", subset=["EPA_Adv"])
                .format("{:.2f}", subset=["YPP_Adv", "PPD_Adv"])
                .map(matchup_rag(matchup_df, "Total"), subset=["Total"])
                .map(matchup_rag(matchup_df, "ITT"), subset=["ITT"])
                .map(spread_color, subset=["Spread"])
                .map(matchup_rag(matchup_df, "Pace"), subset=["Pace"])
                .map(matchup_rag(matchup_df, "Pass%"), subset=["Pass%"])
                .map(proe_color, subset=["PROE"])
                .map(matchup_rag(matchup_df, "EPA_Adv"), subset=["EPA_Adv"])
                .map(matchup_rag(matchup_df, "YPP_Adv"), subset=["YPP_Adv"])
                .map(matchup_rag(matchup_df, "PPD_Adv"), subset=["PPD_Adv"])
                .map(matchup_rag(matchup_df, "Explosive_Adv"), subset=["Explosive_Adv"])
                .map(matchup_rag(matchup_df, "DCR_Adv"), subset=["DCR_Adv"])
            )
        
            st.dataframe(styled_matchups, width="stretch")
        
            # Game-level summary
            st.divider()
            st.subheader("🎯 Top Game Environments")
        
            # Aggregate by game for quick summary
            game_summary = matchup_df.groupby("Game").agg({
                "Total": "first",
                "Pace": "first",
                "EPA_Adv": "mean"
            }).reset_index()
            game_summary = game_summary.sort_values(["Total", "Pace"], ascending=[False, False]).head(5)
        
            col1, col2, col3 = st.columns(3)
            for idx, (_, game) in enumerate(game_summary.iterrows()):
                if idx < 3:
                    with [col1, col2, col3][idx]:
                        st.metric(
                            game["Game"],
                            f"O/U: {game['Total']:.1f}",
                            f"Pace: {game['Pace']:.1f} plays/gm"
                        )
        
            st.download_button(
                "📥 Download Matchup Analysis CSV",
                data=matchup_df.to_csv(index=False),
                file_name="game_matchup_analysis.csv",
                mime="text/csv",
                key="download_matchups"
            )
        else:
            st.warning("⚠️ No matchup data available")


# Standalone execution
if __name__ == "__main__":
    st.set_page_config(page_title="NFL Top Stacks + Boom/Bust Tool", layout="wide")
    run()
