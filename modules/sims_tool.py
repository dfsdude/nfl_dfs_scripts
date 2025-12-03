"""
Comprehensive DFS Lineup Simulator
Simulates entire slate with game environment modeling, player correlations, and field lineups.
Evaluates user lineups against realistic field to compute ROI, cash probability, and top-finish probabilities.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
import warnings

warnings.filterwarnings('ignore')

# Page configuration
# st.set_page_config(page_title="DFS Lineup Simulator", layout="wide", page_icon="📊")


def run():
    """Main entry point for this tool"""
    st.title("📊 DFS Lineup Simulator")
    st.markdown("**Simulate entire slate with game environment modeling and field competition**")

    # ===========================
    # Section 1: Data Ingestion
    # ===========================

    st.sidebar.header("📂 Upload Data Files")

    roo_projections_file = st.sidebar.file_uploader("ROO Projections CSV", type=['csv'], key='roo_projections',
                                                      help="Output from roo_simulator.py with Floor/Ceiling/Median projections")
    matchup_file = st.sidebar.file_uploader("Matchup CSV", type=['csv'], key='matchup')
    lineups_file = st.sidebar.file_uploader("Lineups CSV", type=['csv'], key='lineups')

    st.sidebar.markdown("**Optional: Enhanced Metrics**")
    team_offense_file = st.sidebar.file_uploader("Team Plays Offense CSV", type=['csv'], key='team_offense')
    team_defense_file = st.sidebar.file_uploader("Team Plays Defense CSV", type=['csv'], key='team_defense')

    st.sidebar.header("⚙️ Simulation Parameters")

    # Add preset modes
    sim_mode = st.sidebar.radio("Simulation Mode", ["Quick Test (Fast)", "Standard", "Deep Analysis"], index=1)

    if sim_mode == "Quick Test (Fast)":
        n_sims = st.sidebar.number_input("Number of Simulations", min_value=100, max_value=50000, value=500, step=100)
        field_size = st.sidebar.number_input("Contest Field Size", min_value=2, max_value=500000, value=11890, step=100)
        field_sample_pct = 2.0  # Sample 2% for quick tests
    elif sim_mode == "Standard":
        n_sims = st.sidebar.number_input("Number of Simulations", min_value=100, max_value=50000, value=2000, step=500)
        field_size = st.sidebar.number_input("Contest Field Size", min_value=2, max_value=500000, value=11890, step=100)
        field_sample_pct = 5.0  # Sample 5% for standard
    else:  # Deep Analysis
        n_sims = st.sidebar.number_input("Number of Simulations", min_value=100, max_value=50000, value=5000, step=500)
        field_size = st.sidebar.number_input("Contest Field Size", min_value=2, max_value=500000, value=11890, step=100)
        field_sample_pct = 10.0  # Sample 10% for deep analysis

    entry_fee = st.sidebar.number_input("Entry Fee ($)", min_value=1, max_value=10000, value=3, step=1)

    # Warning for heavy workloads
    field_size_sim = max(150, int(field_size * (field_sample_pct / 100)))
    total_work = n_sims * field_size_sim
    if total_work > 5_000_000:
        st.sidebar.warning(f"⚠️ High workload: {n_sims:,} sims × {field_size_sim:,} lineups = {total_work:,} operations. Consider Quick Test mode for faster results.")

    st.sidebar.subheader("💰 Payout Structure")
    payout_type = st.sidebar.radio("Contest Type", ["Double-Up", "50/50", "Flat GPP", "Top-Heavy GPP", "Custom"])

    payout_structure = {}
    payout_presets = {
        "NFL $40K Front Four (11890 entries, $3)": "1-1:4000\n2-2:2000\n3-3:1500\n4-4:1000\n5-5:750\n6-6:600\n7-8:500\n9-10:400\n11-12:300\n13-14:250\n15-16:200\n17-21:150\n22-26:100\n27-31:75\n32-36:60\n37-46:50\n47-56:40\n57-71:30\n72-96:25\n97-151:20\n152-291:15\n292-661:10\n662-1396:8\n1397-3091:6",
        "Flat GPP (2972 entries, $3)": "1-1:1000\n2-2:500\n3-3:300\n4-4:200\n5-5:150\n6-7:125\n8-10:100\n11-13:75\n14-16:60\n17-20:50\n21-25:40\n26-30:30\n31-45:25\n46-75:20\n76-125:15\n126-230:10\n231-410:8\n411-765:6",
        "Top-Heavy GPP (83234 entries, $5)": "1-1:50000\n2-2:20000\n3-3:10000\n4-4:7500\n5-5:5000\n6-6:3000\n7-8:2000\n9-10:1500\n11-15:1000\n16-20:750\n21-30:500\n31-50:300\n51-70:200\n71-100:100\n101-150:70\n151-225:50\n226-350:40\n351-550:30\n551-1050:25\n1051-1750:20\n1751-3150:15\n3151-6000:12\n6001-10080:10\n10081-20080:8"
    }

    if payout_type == "Double-Up":
        # Double-up: top 44.4% get 2x entry (minus rake)
        cash_line = int(field_size * 0.444)
        payout_multiplier = 1.8  # Accounting for ~10% rake
        for rank in range(1, cash_line + 1):
            payout_structure[rank] = entry_fee * payout_multiplier
        st.sidebar.info(f"Top {cash_line} positions cash (44.4% of field)")

    elif payout_type == "50/50":
        # 50/50: top 50% get 2x entry (minus rake)
        cash_line = int(field_size * 0.50)
        payout_multiplier = 1.8  # Accounting for ~10% rake
        for rank in range(1, cash_line + 1):
            payout_structure[rank] = entry_fee * payout_multiplier
        st.sidebar.info(f"Top {cash_line} positions cash (50% of field)")

    elif payout_type == "Flat GPP":
        # Preset flat payout structure
        preset_choice = st.sidebar.selectbox("Select Preset", ["NFL $40K Front Four (11890 entries, $3)", "Flat GPP (2972 entries, $3)", "Custom"])
    
        if preset_choice == "Custom":
            payout_input = st.sidebar.text_area(
                "Payout Ranges (rank_start-rank_end:payout)",
                value="1-1:4000\n2-2:2000\n3-3:1500\n4-4:1000\n5-5:750\n6-6:600\n7-8:500\n9-10:400\n11-12:300\n13-14:250\n15-16:200\n17-21:150\n22-26:100\n27-31:75\n32-36:60\n37-46:50\n47-56:40\n57-71:30\n72-96:25\n97-151:20\n152-291:15\n292-661:10\n662-1396:8\n1397-3091:6",
                height=200
            )
        else:
            payout_input = payout_presets[preset_choice]
            st.sidebar.text_area("Payout Ranges", value=payout_input, height=200, disabled=True)
    
        # Parse payout structure
        try:
            for line in payout_input.strip().split('\n'):
                if line.strip():
                    range_part, payout = line.split(':')
                    start, end = map(int, range_part.split('-'))
                    payout_val = float(payout)
                    for rank in range(start, end + 1):
                        payout_structure[rank] = payout_val
        
            total_paid = sum(payout_structure.values())
            pct_paid = (len(payout_structure) / field_size) * 100
            st.sidebar.success(f"✅ {len(payout_structure)} positions pay ({pct_paid:.1f}% of field)\n\nTotal Prize Pool: ${total_paid:,.2f}")
        except Exception as e:
            st.sidebar.error(f"Error parsing payout structure: {e}")

    elif payout_type == "Top-Heavy GPP":
        # Preset top-heavy payout structure
        preset_choice = st.sidebar.selectbox("Select Preset", ["Custom", "Top-Heavy GPP (83234 entries, $5)"])
    
        if preset_choice == "Custom":
            payout_input = st.sidebar.text_area(
                "Payout Ranges (rank_start-rank_end:payout)",
                value="1-1:50000\n2-2:20000\n3-3:10000\n4-4:7500\n5-5:5000\n6-6:3000\n7-8:2000\n9-10:1500\n11-15:1000\n16-20:750\n21-30:500\n31-50:300\n51-70:200\n71-100:100\n101-150:70\n151-225:50\n226-350:40\n351-550:30\n551-1050:25\n1051-1750:20\n1751-3150:15\n3151-6000:12\n6001-10080:10\n10081-20080:8",
                height=200
            )
        else:
            payout_input = payout_presets[preset_choice]
            st.sidebar.text_area("Payout Ranges", value=payout_input, height=200, disabled=True)
    
        # Parse payout structure
        try:
            for line in payout_input.strip().split('\n'):
                if line.strip():
                    range_part, payout = line.split(':')
                    start, end = map(int, range_part.split('-'))
                    payout_val = float(payout)
                    for rank in range(start, end + 1):
                        payout_structure[rank] = payout_val
        
            total_paid = sum(payout_structure.values())
            pct_paid = (len(payout_structure) / field_size) * 100
            st.sidebar.success(f"✅ {len(payout_structure)} positions pay ({pct_paid:.1f}% of field)\n\nTotal Prize Pool: ${total_paid:,.2f}")
        except Exception as e:
            st.sidebar.error(f"Error parsing payout structure: {e}")

    else:  # Custom
        st.sidebar.markdown("**Enter payout structure**")
        st.sidebar.markdown("*Format: `1-1:1000` or `6-7:125` or `411-765:6`*")
    
        payout_input = st.sidebar.text_area(
            "Payout Ranges (rank_start-rank_end:payout)",
            value="1-1:1000\n2-2:500\n3-3:300\n4-4:200\n5-5:150",
            height=200
        )
    
        # Parse payout structure
        try:
            for line in payout_input.strip().split('\n'):
                if line.strip():
                    range_part, payout = line.split(':')
                    start, end = map(int, range_part.split('-'))
                    payout_val = float(payout)
                    for rank in range(start, end + 1):
                        payout_structure[rank] = payout_val
        
            total_paid = sum(payout_structure.values())
            pct_paid = (len(payout_structure) / field_size) * 100
            st.sidebar.success(f"✅ {len(payout_structure)} positions pay ({pct_paid:.1f}% of field)\n\nTotal Prize Pool: ${total_paid:,.2f}")
        except Exception as e:
            st.sidebar.error(f"Error parsing payout structure: {e}")

    st.sidebar.subheader("Environment Parameters")
    total_sd = st.sidebar.slider("Total Volatility (SD)", min_value=1.0, max_value=15.0, value=7.0, step=0.5, 
                                  help="Game total variance - higher values = more unpredictable scoring (typical: 5-8 points)")
    spread_sd = st.sidebar.slider("Spread Volatility (SD)", min_value=1.0, max_value=10.0, value=4.0, step=0.5,
                                   help="Point spread variance - how much game margins deviate from projected spread (typical: 3-5 points)")
    alpha_matchup = st.sidebar.slider("Matchup Strength Impact (α)", min_value=0.0, max_value=0.2, value=0.05, step=0.01,
                                       help="Weight of team strength metrics (EPA, YPP, etc.) on scoring - 0.05 = 5% boost for elite offenses")

    st.sidebar.subheader("Correlation Settings")
    use_correlations = st.sidebar.checkbox("Enable Player Correlations", value=True,
                                           help="Apply QB-WR stacking correlation and game script correlations")
    qb_pass_corr = st.sidebar.slider("QB-Pass Catcher Correlation", min_value=0.0, max_value=0.5, value=0.35, step=0.05,
                                      help="Boost to same-team WR/TE when QB outperforms (0.35 = 10-30% boost when QB booms)")

    # Helper function: find column with variants
    def find_column(df, variants):
        """Find first matching column from list of variants"""
        for variant in variants:
            matches = [col for col in df.columns if variant.lower() in col.lower()]
            if matches:
                return matches[0]
        return None

    # Load data
    if roo_projections_file and matchup_file and lineups_file:
        try:
            # Load ROO projections (contains all player data)
            players_df = pd.read_csv(roo_projections_file)
        
            # Find player name column
            name_col = find_column(players_df, ['Player', 'Name', 'player', 'name'])
            if name_col is None:
                st.error("ROO Projections CSV missing player name column (Player, Name, etc.)")
                st.stop()
        
            # Standardize to 'Name'
            if name_col != 'Name':
                players_df = players_df.rename(columns={name_col: 'Name'})
        
            # Map ROO projection columns to expected simulator columns
            column_mapping = {
                'OWS_Median_Proj': 'median_proj',  # ROO median projection
                'Ceiling_Proj': 'ceiling_proj',     # ROO ceiling (P85)
                'Floor_Proj': 'floor_proj',         # ROO floor (P15)
                'Volatility_Index': 'var_dk',       # ROO volatility measure
                'stddev_adj': 'var_dk',             # Alternative: use stddev_adj if Volatility_Index missing
                'Own%': 'Proj_Own',                 # Ownership percentage
                'dk_ownership': 'Proj_Own',         # Alternative ownership column
            }
            
            # Apply mapping (only rename columns that exist)
            existing_mappings = {old: new for old, new in column_mapping.items() if old in players_df.columns}
            players_df = players_df.rename(columns=existing_mappings)
            
            # Ensure required columns exist
            required_player_cols = ['Name', 'Position', 'Team', 'Salary']
            if not all(col in players_df.columns for col in required_player_cols):
                missing = [col for col in required_player_cols if col not in players_df.columns]
                st.error(f"ROO Projections CSV missing required columns: {missing}")
                st.stop()
        
            # Check for projection columns
            if 'median_proj' not in players_df.columns:
                st.error("ROO Projections CSV missing median projection column (OWS_Median_Proj)")
                st.stop()
        
            # Check for ownership
            if 'Proj_Own' not in players_df.columns:
                st.warning("⚠️ No ownership column found - using uniform 5% ownership for all players")
                players_df['Proj_Own'] = 5.0
        
            # Convert ownership to percentage if needed
            if players_df['Proj_Own'].max() <= 1.0:
                players_df['Proj_Own'] = players_df['Proj_Own'] * 100
        
            # Use ROO ceiling if available, otherwise calculate
            if 'ceiling_proj' not in players_df.columns:
                players_df['ceiling_proj'] = players_df['median_proj'] * 1.5
        
            # Use ROO volatility measure if available
            if 'var_dk' not in players_df.columns:
                # Fallback: estimate variance from ceiling/median spread
                players_df['var_dk'] = (players_df['ceiling_proj'] - players_df['median_proj']) / 2
        
            # ROO projections already include historical volatility analysis
            # No need for separate weekly stats file
            st.success(f"✅ Loaded {len(players_df)} players from ROO projections")
        
            # Load matchup data
            matchup_df = pd.read_csv(matchup_file)
        
            # Find team column
            team_col = find_column(matchup_df, ['Init', 'Team', 'team'])
            if team_col is None:
                st.error("Matchup CSV missing team column (Init, Team, etc.)")
                st.stop()
        
            # Standardize column names
            if team_col != 'Team':
                matchup_df = matchup_df.rename(columns={team_col: 'Team'})
        
            # Verify required columns
            if 'Opp' not in matchup_df.columns:
                st.error("Matchup CSV missing 'Opp' column")
                st.stop()
        
            if 'Total' not in matchup_df.columns:
                st.error("Matchup CSV missing 'Total' column")
                st.stop()
        
            # Load lineups
            lineups_df = pd.read_csv(lineups_file)
        
            # Debug: show actual columns
            st.info(f"Detected columns: {lineups_df.columns.tolist()}")
        
            # Check for DK format with duplicate column names
            # Pandas reads "QB,RB,RB,WR,WR,WR,TE,FLEX,DST" as "QB,RB,RB.1,WR,WR.1,WR.2,TE,FLEX,DST"
            if 'RB.1' in lineups_df.columns or ('RB' in lineups_df.columns and 'RB1' not in lineups_df.columns):
                # Rename DK format columns to standard format
                col_mapping = {}
            
                # Handle RB columns
                if 'RB' in lineups_df.columns:
                    col_mapping['RB'] = 'RB1'
                if 'RB.1' in lineups_df.columns:
                    col_mapping['RB.1'] = 'RB2'
            
                # Handle WR columns
                if 'WR' in lineups_df.columns:
                    col_mapping['WR'] = 'WR1'
                if 'WR.1' in lineups_df.columns:
                    col_mapping['WR.1'] = 'WR2'
                if 'WR.2' in lineups_df.columns:
                    col_mapping['WR.2'] = 'WR3'
            
                lineups_df = lineups_df.rename(columns=col_mapping)
        
            # Validate lineups have required columns
            position_cols = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE', 'FLEX', 'DST']
            if not all(col in lineups_df.columns for col in position_cols):
                st.error(f"Lineups CSV missing required position columns: {position_cols}")
                st.error(f"Available columns: {lineups_df.columns.tolist()}")
                st.stop()
        
            # Strip DraftKings IDs from player names (e.g., "Patrick Mahomes (40924875)" -> "Patrick Mahomes")
            for col in position_cols:
                lineups_df[col] = lineups_df[col].str.replace(r'\s*\(\d+\)', '', regex=True)
        
            # Load optional team stats
            team_offense_df = None
            team_defense_df = None
        
            if team_offense_file:
                team_offense_df = pd.read_csv(team_offense_file)
                st.success(f"✅ Loaded team offense stats for {len(team_offense_df)} teams")
        
            if team_defense_file:
                team_defense_df = pd.read_csv(team_defense_file)
                st.success(f"✅ Loaded team defense stats for {len(team_defense_df)} teams")
        
            st.success(f"✅ Loaded {len(players_df)} players, {len(weekly_stats_df)} historical records, {len(matchup_df)} matchups, {len(lineups_df)} lineups")
        
            # ===========================
            # Section 2: Player Mapping
            # ===========================
        
            st.header("📋 Data Processing")
        
            # Create player ID mapping for NumPy vectorization
            unique_players = players_df['Name'].unique()
            player_to_id = {name: idx for idx, name in enumerate(unique_players)}
            id_to_player = {idx: name for name, idx in player_to_id.items()}
            n_players = len(player_to_id)
        
            st.info(f"Created player ID mapping for {n_players} players")
        
            with st.spinner("Building player history and matchup mapping..."):
                # Build player_hist dict with recency-weighted metrics
                lambda_decay = 0.15
                max_week = weekly_stats_df['Week'].max()
            
                player_hist = {}
            
                for player_name in players_df['Name'].unique():
                    player_stats = weekly_stats_df[weekly_stats_df['Name'] == player_name].copy()
                
                    if len(player_stats) >= 3:  # Need at least 3 games for meaningful history
                        # Calculate recency weights
                        player_stats['weight'] = np.exp(-lambda_decay * (max_week - player_stats['Week']))
                    
                        scores = player_stats['DK Points'].values
                        weights = player_stats['weight'].values
                    
                        # Normalize weights
                        weights = weights / weights.sum()
                    
                        # Weighted statistics
                        weighted_mean = np.sum(scores * weights)
                        weighted_var = np.sum(weights * (scores - weighted_mean)**2)
                        weighted_std = np.sqrt(weighted_var)
                    
                        # 90th percentile (simple: sort and take weighted position)
                        sorted_idx = np.argsort(scores)
                        sorted_scores = scores[sorted_idx]
                        sorted_weights = weights[sorted_idx]
                        cumsum = np.cumsum(sorted_weights)
                        p90_idx = np.searchsorted(cumsum, 0.90)
                        p90 = sorted_scores[min(p90_idx, len(sorted_scores)-1)]
                    
                        player_hist[player_name] = {
                            'scores': scores,
                            'weights': weights,
                            'mean': weighted_mean,
                            'std': weighted_std,
                            'p90': p90,
                            'n_games': len(scores)
                        }
            
                # Build team_env dict from matchup data
                team_env = {}
            
                # Map metric column names with variants
                metric_mapping = {
                    'EPA': find_column(matchup_df, ['Init_EPA_Play', 'Init_EPA', 'EPA', 'epa']),
                    'YPP': find_column(matchup_df, ['Init_Yards Per Play', 'Init_YPP', 'YPP', 'yards_per_play']),
                    'PPD': find_column(matchup_df, ['Init_Points Per Drive', 'Init_PPD', 'PPD', 'points_per_drive']),
                    'Explosive': find_column(matchup_df, ['Init_Explosive Play Rate', 'Init_Explosive', 'Explosive', 'explosive_rate']),
                    'Conv': find_column(matchup_df, ['Init_Down Conversion Rate', 'Init_Conv', 'Conv', 'conversion_rate'])
                }
            
                # Calculate z-scores for matchup metrics
                for metric_name, col_name in metric_mapping.items():
                    if col_name and col_name in matchup_df.columns:
                        mean_val = matchup_df[col_name].mean()
                        std_val = matchup_df[col_name].std()
                        matchup_df[f'{metric_name}_z'] = (matchup_df[col_name] - mean_val) / (std_val + 1e-6)
                    else:
                        matchup_df[f'{metric_name}_z'] = 0.0
            
                for _, row in matchup_df.iterrows():
                    team = row['Team']
                    opp = row['Opp']
                
                    # Calculate overall matchup strength
                    ovr_matchup_strength = (
                        0.3 * matchup_df.loc[matchup_df['Team'] == team, 'EPA_z'].values[0] +
                        0.2 * matchup_df.loc[matchup_df['Team'] == team, 'YPP_z'].values[0] +
                        0.2 * matchup_df.loc[matchup_df['Team'] == team, 'PPD_z'].values[0] +
                        0.15 * matchup_df.loc[matchup_df['Team'] == team, 'Explosive_z'].values[0] +
                        0.15 * matchup_df.loc[matchup_df['Team'] == team, 'Conv_z'].values[0]
                    )
                
                    # Base expected points (from total)
                    total = row['Total'] if 'Total' in row and pd.notna(row['Total']) else 45.0
                    spread = row['Spread'] if 'Spread' in row and pd.notna(row['Spread']) else 0.0
                
                    base_points = (total + spread) / 2 if spread != 0 else total / 2
                
                    # Volatility z-score (higher spread = higher volatility)
                    volatility_z = abs(spread) / 7.0 if spread != 0 else 0.0
                
                    # Get team offense stats if available
                    team_offense_stats = {}
                    if team_offense_df is not None and 'Team' in team_offense_df.columns:
                        team_off = team_offense_df[team_offense_df['Team'] == team]
                        if len(team_off) > 0:
                            team_offense_stats = {
                                'avg_plays': team_off['Avg Plays'].values[0],
                                'avg_pass_att': team_off['Avg Pass Att'].values[0],
                                'avg_rush_att': team_off['Avg Rush Att'].values[0],
                                'avg_pass_yds': team_off['Avg Pass Yds'].values[0],
                                'avg_rush_yds': team_off['Avg Rush Yds'].values[0],
                                'avg_pass_1std': team_off['Avg Pass 1stD'].values[0],
                                'avg_rush_1std': team_off['Avg Rush 1stD'].values[0],
                                'avg_rush_td': team_off['Avg_Rush_TD'].values[0],
                                'avg_pass_td': team_off['Avg_Pass_TD'].values[0]
                            }
                
                    # Get opponent defense stats if available
                    opp_defense_stats = {}
                    if team_defense_df is not None and 'Opp' in team_defense_df.columns:
                        opp_def = team_defense_df[team_defense_df['Opp'] == team]
                        if len(opp_def) > 0:
                            opp_defense_stats = {
                                'opp_avg_plays': opp_def['Avg Plays'].values[0],
                                'opp_avg_pass_att': opp_def['Avg Pass Att'].values[0],
                                'opp_avg_rush_att': opp_def['Avg Rush Att'].values[0],
                                'opp_avg_pass_yds': opp_def['Avg Pass Yds'].values[0],
                                'opp_avg_rush_yds': opp_def['Avg Rush Yds'].values[0],
                                'opp_avg_pass_1std': opp_def['Avg Pass 1stD'].values[0],
                                'opp_avg_rush_1std': opp_def['Avg Rush 1stD'].values[0],
                                'opp_avg_rush_td': opp_def['Avg_Rush_TD'].values[0],
                                'opp_avg_pass_td': opp_def['Avg_Pass_TD'].values[0]
                            }
                
                    team_env[team] = {
                        'opp': opp,
                        'total': total,
                        'spread': spread,
                        'base_points': base_points,
                        'ovr_matchup_strength': ovr_matchup_strength,
                        'volatility_z': volatility_z,
                        'offense_stats': team_offense_stats,
                        'defense_vs_stats': opp_defense_stats
                    }
            
                st.success(f"✅ Built history for {len(player_hist)} players and matchup environment for {len(team_env)} teams")
        
            # ===========================
            # Section 3: Sampling Functions
            # ===========================
        
            def sample_player_score(player_name, player_row, player_hist, rng):
                """Sample a player's score using empirical distribution with projection scaling"""
            
                median_proj = player_row['median_proj']
            
                if player_name in player_hist:
                    hist = player_hist[player_name]
                
                    # Empirical sampling with recency weights
                    raw_score = rng.choice(hist['scores'], p=hist['weights'])
                
                    # Scale to projection
                    scale = median_proj / max(hist['mean'], 0.1)
                    base_score = raw_score * scale
                
                    return base_score
            
                else:
                    # Parametric fallback using var_dk or position-based variance
                    if 'var_dk' in player_row and pd.notna(player_row['var_dk']) and player_row['var_dk'] > 0:
                        std_dev = np.sqrt(player_row['var_dk'])
                    else:
                        # Position-based variance estimation
                        ceiling = player_row['ceiling_proj']
                        position = player_row['Position']
                    
                        # Try ceiling-based estimate first
                        if ceiling > median_proj and (ceiling - median_proj) < median_proj * 2:
                            std_dev = (ceiling - median_proj) / 1.65
                        else:
                            # Position multipliers (variance as % of projection)
                            pos_mult = {
                                'QB': 0.45,
                                'RB': 0.60,
                                'WR': 0.65,
                                'TE': 0.55,
                                'DST': 0.70
                            }
                            mult = pos_mult.get(position, 0.60)
                            std_dev = median_proj * mult
                
                    # Sample from normal distribution
                    base_score = rng.normal(median_proj, std_dev)
                    base_score = max(0, base_score)  # No negative scores
                
                    return base_score
        
            def apply_team_adjustments(player_row, base_score, team_env):
                """Apply position-specific adjustments based on team offense/defense stats"""
            
                team = player_row['Team']
                position = player_row['Position']
            
                if team not in team_env:
                    return base_score
            
                env = team_env[team]
                offense_stats = env.get('offense_stats', {})
                defense_vs_stats = env.get('defense_vs_stats', {})
            
                if not offense_stats and not defense_vs_stats:
                    return base_score
            
                adjustment = 1.0
            
                # QB adjustments
                if position == 'QB' and offense_stats:
                    # More pass attempts = higher QB scoring potential
                    avg_pass_att = offense_stats.get('avg_pass_att', 30)
                    if avg_pass_att > 35:
                        adjustment *= 1.05
                    elif avg_pass_att < 27:
                        adjustment *= 0.95
                
                    # Pass TD rate impact
                    avg_pass_td = offense_stats.get('avg_pass_td', 1.5)
                    if avg_pass_td > 2.0:
                        adjustment *= 1.08
                    elif avg_pass_td < 1.0:
                        adjustment *= 0.92
            
                # RB adjustments
                elif position == 'RB' and offense_stats:
                    # More rush attempts = higher RB scoring
                    avg_rush_att = offense_stats.get('avg_rush_att', 25)
                    if avg_rush_att > 28:
                        adjustment *= 1.08
                    elif avg_rush_att < 22:
                        adjustment *= 0.92
                
                    # Rush TD rate impact
                    avg_rush_td = offense_stats.get('avg_rush_td', 1.0)
                    if avg_rush_td > 1.3:
                        adjustment *= 1.05
                    elif avg_rush_td < 0.7:
                        adjustment *= 0.95
            
                # WR/TE adjustments
                elif position in ['WR', 'TE'] and offense_stats:
                    # Pass-heavy offenses benefit pass catchers
                    avg_pass_att = offense_stats.get('avg_pass_att', 30)
                    if avg_pass_att > 35:
                        adjustment *= 1.06
                    elif avg_pass_att < 27:
                        adjustment *= 0.94
                
                    # Pass yards impact
                    avg_pass_yds = offense_stats.get('avg_pass_yds', 220)
                    if avg_pass_yds > 260:
                        adjustment *= 1.04
                    elif avg_pass_yds < 200:
                        adjustment *= 0.96
            
                # DST adjustments (based on opponent offense)
                elif position == 'DST' and defense_vs_stats:
                    # Opponent's offensive output (defense allows more = DST has more opportunities)
                    opp_pass_yds = defense_vs_stats.get('opp_avg_pass_yds', 220)
                    opp_rush_yds = defense_vs_stats.get('opp_avg_rush_yds', 115)
                
                    # Lower yards allowed = better DST matchup
                    if opp_pass_yds < 200 and opp_rush_yds < 100:
                        adjustment *= 1.15
                    elif opp_pass_yds > 260 or opp_rush_yds > 140:
                        adjustment *= 0.85
            
                return base_score * adjustment
        
            # ===========================
            # Section 4: Game Environment Simulation
            # ===========================
        
            def build_env_state(team_env, matchup_df, total_sd, spread_sd, alpha_matchup, rng):
                """Build game environment state for one simulation"""
            
                env_state = {}
            
                # Get unique games
                games = matchup_df[['Team', 'Opp']].copy()
                games['game_id'] = games.apply(lambda r: tuple(sorted([r['Team'], r['Opp']])), axis=1)
                unique_games = games.drop_duplicates('game_id')
            
                for _, game_row in unique_games.iterrows():
                    game_id = game_row['game_id']
                    t1, t2 = game_id
                
                    # Get base values
                    t1_base = team_env[t1]['base_points']
                    t2_base = team_env[t2]['base_points']
                    total_base = team_env[t1]['total']
                    spread_base = team_env[t1]['spread']
                
                    # Sample game environment with noise
                    total_sim = rng.normal(total_base, total_sd)
                    total_sim = max(total_sim, 10.0)  # Minimum 10 points total
                
                    spread_sim = rng.normal(spread_base, spread_sd)
                
                    # Calculate simulated team points
                    t1_points_sim = (total_sim + spread_sim) / 2
                    t2_points_sim = (total_sim - spread_sim) / 2
                
                    # Apply matchup strength adjustment
                    t1_strength = team_env[t1]['ovr_matchup_strength']
                    t2_strength = team_env[t2]['ovr_matchup_strength']
                
                    t1_points_sim *= (1 + alpha_matchup * t1_strength)
                    t2_points_sim *= (1 + alpha_matchup * t2_strength)
                
                    # Renormalize to match total_sim
                    current_total = t1_points_sim + t2_points_sim
                    renorm = total_sim / max(current_total, 1.0)
                    t1_points_sim *= renorm
                    t2_points_sim *= renorm
                
                    # Store environment state
                    env_state[game_id] = {
                        'points': {t1: t1_points_sim, t2: t2_points_sim},
                        'total_sim': total_sim,
                        'spread_sim': spread_sim,
                        'team_scoring_mult': {
                            t1: t1_points_sim / max(t1_base, 1.0),
                            t2: t2_points_sim / max(t2_base, 1.0)
                        },
                        'volatility_z': {
                            t1: team_env[t1]['volatility_z'],
                            t2: team_env[t2]['volatility_z']
                        }
                    }
            
                return env_state
        
            # ===========================
            # Section 5: Correlation Adjustments
            # ===========================
        
            def apply_correlations(lineup_players, sim_scores, players_df, env_state, qb_pass_corr, rng):
                """Apply correlation adjustments to player scores"""
            
                # Build lineup dataframe
                lineup_df = players_df[players_df['Name'].isin(lineup_players)].copy()
                lineup_df['sim_score'] = lineup_df['Name'].map(sim_scores)
            
                # QB-pass catcher correlation
                qbs = lineup_df[lineup_df['Position'] == 'QB']
            
                for _, qb_row in qbs.iterrows():
                    qb_name = qb_row['Name']
                    qb_team = qb_row['Team']
                    qb_score = sim_scores[qb_name]
                    qb_median = qb_row['median_proj']
                
                    # Find pass catchers on same team
                    pass_catchers = lineup_df[
                        (lineup_df['Position'].isin(['WR', 'TE'])) & 
                        (lineup_df['Team'] == qb_team) &
                        (lineup_df['Name'] != qb_name)
                    ]
                
                    for _, pc_row in pass_catchers.iterrows():
                        pc_name = pc_row['Name']
                        pc_score = sim_scores[pc_name]
                        pc_median = pc_row['median_proj']
                    
                        # If QB booms, nudge pass catchers up
                        if qb_score > 1.5 * qb_median:
                            boost = rng.uniform(1.1, 1.3)
                            sim_scores[pc_name] = pc_score * boost
                    
                        # If QB busts, nudge pass catchers down
                        elif qb_score < 0.5 * qb_median:
                            penalty = rng.uniform(0.7, 0.9)
                            sim_scores[pc_name] = pc_score * penalty
            
                # RB + team total correlation
                rbs = lineup_df[lineup_df['Position'] == 'RB']
            
                for _, rb_row in rbs.iterrows():
                    rb_name = rb_row['Name']
                    rb_team = rb_row['Team']
                    rb_score = sim_scores[rb_name]
                
                    # Find game for this team
                    game_id = None
                    for gid in env_state:
                        if rb_team in gid:
                            game_id = gid
                            break
                
                    if game_id:
                        team_mult = env_state[game_id]['team_scoring_mult'][rb_team]
                    
                        # If team scoring high, boost RB slightly
                        if team_mult > 1.2:
                            sim_scores[rb_name] = rb_score * rng.uniform(1.05, 1.15)
                        elif team_mult < 0.8:
                            sim_scores[rb_name] = rb_score * rng.uniform(0.85, 0.95)
            
                return sim_scores
        
            # ===========================
            # Section 6: Field Lineup Generation
            # ===========================
        
            def generate_field_lineups(players_df, field_size_sim, rng):
                """Generate ownership-weighted field lineups"""
            
                lineups = []
                max_attempts = field_size_sim * 5  # Increased multiplier for better success rate
                attempts = 0
            
                # Separate players by position and filter valid candidates
                qbs = players_df[(players_df['Position'] == 'QB') & (players_df['Proj_Own'] > 0)].copy()
                rbs = players_df[(players_df['Position'] == 'RB') & (players_df['Proj_Own'] > 0)].copy()
                wrs = players_df[(players_df['Position'] == 'WR') & (players_df['Proj_Own'] > 0)].copy()
                tes = players_df[(players_df['Position'] == 'TE') & (players_df['Proj_Own'] > 0)].copy()
                dsts = players_df[(players_df['Position'] == 'DST') & (players_df['Proj_Own'] > 0)].copy()
            
                # Ownership-based probabilities
                qb_probs = qbs['Proj_Own'].values / qbs['Proj_Own'].sum()
                rb_probs = rbs['Proj_Own'].values / rbs['Proj_Own'].sum()
                wr_probs = wrs['Proj_Own'].values / wrs['Proj_Own'].sum()
                te_probs = tes['Proj_Own'].values / tes['Proj_Own'].sum()
                dst_probs = dsts['Proj_Own'].values / dsts['Proj_Own'].sum()
            
                # Pre-compute salary lookup for faster access
                # Pre-compute salary lookup for faster access
                player_salary = dict(zip(players_df['Name'], players_df['Salary']))
            
                while len(lineups) < field_size_sim and attempts < max_attempts:
                    attempts += 1
                
                    try:
                        # Sample positions
                        qb = rng.choice(qbs['Name'].values, p=qb_probs)
                        rb1, rb2 = rng.choice(rbs['Name'].values, size=2, replace=False, p=rb_probs)
                        wr1, wr2, wr3 = rng.choice(wrs['Name'].values, size=3, replace=False, p=wr_probs)
                        te = rng.choice(tes['Name'].values, p=te_probs)
                        dst = rng.choice(dsts['Name'].values, p=dst_probs)
                    
                        # FLEX: choose from remaining RBs/WRs/TEs
                        flex_pool = pd.concat([
                            rbs[~rbs['Name'].isin([rb1, rb2])],
                            wrs[~wrs['Name'].isin([wr1, wr2, wr3])],
                            tes[~tes['Name'].isin([te])]
                        ])
                    
                        if len(flex_pool) == 0:
                            continue
                    
                        flex_probs = flex_pool['Proj_Own'].values / flex_pool['Proj_Own'].sum()
                        flex = rng.choice(flex_pool['Name'].values, p=flex_probs)
                    
                        # Build lineup
                        lineup_players = [qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst]
                    
                        # Fast salary check using pre-computed dict
                        total_salary = sum(player_salary.get(p, 0) for p in lineup_players)
                    
                        if total_salary <= 50000:
                            lineups.append(lineup_players)
                
                    except Exception as e:
                        continue
            
                return lineups
        
            # ===========================
            # Section 7: Simulation Loop
            # ===========================
        
            if st.button("🚀 Run Simulations", type="primary"):
                with st.spinner(f"Running {n_sims:,} simulations..."):
                
                    # Generate field lineups (once, reused across all sims)
                    # Use field_sample_pct to control field sample size
                    field_size_sim = max(150, int(field_size * (field_sample_pct / 100)))
                    st.info(f"Generating {field_size_sim:,} field lineups ({field_sample_pct}% of {field_size:,} full field)...")
                
                    rng = np.random.default_rng(42)
                    field_lineups = generate_field_lineups(players_df, field_size_sim, rng)
                
                    st.success(f"✅ Generated {len(field_lineups):,} valid field lineups")
                
                    # Convert user lineups to list of player lists
                    user_lineups = []
                    for _, row in lineups_df.iterrows():
                        lineup = [row['QB'], row['RB1'], row['RB2'], row['WR1'], row['WR2'], row['WR3'], row['TE'], row['FLEX'], row['DST']]
                        user_lineups.append(lineup)
                
                    st.info(f"Simulating {len(user_lineups)} user lineup(s)...")
                
                    # Get unique players that appear in any lineup (field + user)
                    all_lineup_players = set()
                    for field_lineup in field_lineups:
                        all_lineup_players.update(field_lineup)
                    for user_lineup in user_lineups:
                        all_lineup_players.update(user_lineup)
                
                    # Check for missing players (in lineups but not in players CSV)
                    missing_players = all_lineup_players - set(players_df['Name'].values)
                    if missing_players:
                        st.error(f"❌ Found {len(missing_players)} player(s) in lineups that are NOT in Players CSV:")
                        for player in sorted(missing_players):
                            st.error(f"   • {player}")
                        st.error("Please ensure all players in your lineups exist in the Players CSV file.")
                        st.stop()
                
                    # Pre-filter players_df to only those in lineups
                    players_in_lineups = players_df[players_df['Name'].isin(all_lineup_players)].copy()
                
                    st.info(f"Optimized to simulate {len(players_in_lineups)} unique players (from {len(players_df)} total)")
                
                    # Pre-build team to game_id mapping for faster lookup
                    team_to_games = {}
                    for _, row in matchup_df.iterrows():
                        team = row['Team']
                        opp = row['Opp']
                        game_id = tuple(sorted([team, opp]))
                        team_to_games[team] = game_id
                
                    # Convert lineups to NumPy integer arrays for vectorized operations
                    field_lineups_ids = np.array([[player_to_id[p] for p in lineup] for lineup in field_lineups], dtype=np.int32)
                    user_lineups_ids = np.array([[player_to_id[p] for p in lineup] for lineup in user_lineups], dtype=np.int32)
                
                    # Pre-build correlation lookups (cache these outside simulation loop)
                    qb_to_pass_catchers = {}  # QB -> list of (pass_catcher_id, median_proj) tuples
                    player_to_team_game = {}  # player_id -> (team, game_id)
                
                    for _, player_row in players_in_lineups.iterrows():
                        player_id = player_to_id[player_row['Name']]
                        player_team = player_row['Team']
                        game_id = team_to_games.get(player_team)
                        player_to_team_game[player_id] = (player_team, game_id)
                    
                        # Build QB -> pass catcher mapping
                        if player_row['Position'] == 'QB':
                            # Find pass catchers on same team that are in lineups
                            pass_catchers = players_in_lineups[
                                (players_in_lineups['Position'].isin(['WR', 'TE'])) & 
                                (players_in_lineups['Team'] == player_team)
                            ]
                            qb_to_pass_catchers[player_id] = [
                                (player_to_id[pc_name], pc_median) 
                                for pc_name, pc_median in zip(pass_catchers['Name'], pass_catchers['median_proj'])
                            ]
                
                    st.info("✅ Pre-computed correlation lookups for vectorized operations")
                
                    # Create player metadata arrays for fast access
                    player_medians = np.zeros(n_players)
                    player_positions = {}
                    for _, row in players_in_lineups.iterrows():
                        player_id = player_to_id[row['Name']]
                        player_medians[player_id] = row['median_proj']
                        player_positions[player_id] = row['Position']
                
                    # Results storage
                    sim_results = {i: [] for i in range(len(user_lineups))}
                
                    # Progress bar
                    progress_bar = st.progress(0)
                
                    # Run simulations
                    for sim_idx in range(n_sims):
                        # Update progress every 100 sims
                        if sim_idx % 100 == 0:
                            progress_bar.progress(min(sim_idx / n_sims, 1.0))
                    
                        # Build environment state for this sim
                        env_state = build_env_state(team_env, matchup_df, total_sd, spread_sd, alpha_matchup, rng)
                    
                        # Sample scores as NumPy array indexed by player_id (MUCH faster than dict)
                        sim_scores_array = np.zeros(n_players, dtype=np.float32)
                    
                        for _, player_row in players_in_lineups.iterrows():
                            player_name = player_row['Name']
                            player_id = player_to_id[player_name]
                        
                            base_score = sample_player_score(player_name, player_row, player_hist, rng)
                        
                            # Apply team-based adjustments (pace, tendencies)
                            base_score = apply_team_adjustments(player_row, base_score, team_env)
                        
                            # Apply environment multiplier using pre-built mapping
                            player_team, game_id = player_to_team_game[player_id]
                        
                            if game_id and game_id in env_state:
                                team_mult = env_state[game_id]['team_scoring_mult'][player_team]
                                score_after_env = base_score * team_mult
                            else:
                                score_after_env = base_score
                        
                            sim_scores_array[player_id] = score_after_env
                    
                        # Apply correlations if enabled (vectorized with NumPy arrays)
                        if use_correlations:
                            # QB-pass catcher correlation
                            for qb_id, pass_catchers in qb_to_pass_catchers.items():
                                qb_score = sim_scores_array[qb_id]
                                qb_median = player_medians[qb_id]
                            
                                # If QB booms, nudge pass catchers up
                                if qb_score > 1.5 * qb_median:
                                    for pc_id, pc_median in pass_catchers:
                                        boost = rng.uniform(1.1, 1.3)
                                        sim_scores_array[pc_id] *= boost
                            
                                # If QB busts, nudge pass catchers down
                                elif qb_score < 0.5 * qb_median:
                                    for pc_id, pc_median in pass_catchers:
                                        penalty = rng.uniform(0.7, 0.9)
                                        sim_scores_array[pc_id] *= penalty
                        
                            # RB + team total correlation
                            for player_id, (player_team, game_id) in player_to_team_game.items():
                                if player_positions.get(player_id) == 'RB' and game_id and game_id in env_state:
                                    team_mult = env_state[game_id]['team_scoring_mult'][player_team]
                                
                                    # If team is expected to score more, RB gets small boost
                                    if team_mult > 1.1:
                                        sim_scores_array[player_id] *= rng.uniform(1.05, 1.15)
                                    elif team_mult < 0.9:
                                        sim_scores_array[player_id] *= rng.uniform(0.85, 0.95)
                        
                            # DST + spread correlation
                            for player_id, (player_team, game_id) in player_to_team_game.items():
                                if player_positions.get(player_id) == 'DST' and game_id and game_id in env_state:
                                    spread = env_state[game_id]['spread']
                                    team_names = list(env_state[game_id]['team_scoring_mult'].keys())
                                
                                    # Determine which side of spread
                                    if player_team == team_names[0]:
                                        team_spread = -spread
                                    else:
                                        team_spread = spread
                                
                                    # If favored, DST gets boost
                                    if team_spread < -3:
                                        sim_scores_array[player_id] *= rng.uniform(1.1, 1.2)
                                    elif team_spread > 3:
                                        sim_scores_array[player_id] *= rng.uniform(0.8, 0.9)
                    
                        # VECTORIZED lineup scoring using NumPy array indexing
                        # Field lineups: score = sum of player scores for each lineup
                        field_scores = sim_scores_array[field_lineups_ids].sum(axis=1)
                    
                        # User lineups
                        user_scores = sim_scores_array[user_lineups_ids].sum(axis=1)
                    
                        # Combine and rank
                        all_scores = np.concatenate([field_scores, user_scores])
                        ranks = pd.Series(all_scores).rank(ascending=False, method='min').astype(int).values
                    
                        # Extract user ranks (last N entries)
                        user_ranks = ranks[-len(user_lineups):]
                    
                        # Map ranks to payouts
                        for i, (rank, score) in enumerate(zip(user_ranks, user_scores)):
                            # Scale rank to full field size
                            scaled_rank = int(rank * (field_size / (len(field_lineups) + len(user_lineups))))
                        
                            # Get payout from payout structure (already built based on contest type)
                            payout = payout_structure.get(scaled_rank, 0)
                        
                            profit = payout - entry_fee
                        
                            sim_results[i].append({
                                'score': score,
                                'rank': scaled_rank,
                                'profit': profit
                            })
                
                    progress_bar.progress(1.0)
                
                    # ===========================
                    # Section 8: Results Display
                    # ===========================
                
                    st.header("📊 Simulation Results")
                
                    # Aggregate results per lineup
                    summary_data = []
                
                    for i in range(len(user_lineups)):
                        results = sim_results[i]
                    
                        scores = [r['score'] for r in results]
                        profits = [r['profit'] for r in results]
                        ranks = [r['rank'] for r in results]
                    
                        mean_score = np.mean(scores)
                        mean_profit = np.mean(profits)
                        roi = (mean_profit / entry_fee) * 100
                    
                        cash_count = sum(1 for p in profits if p > 0)
                        prob_cash = (cash_count / n_sims) * 100
                    
                        top10_thresh = int(field_size * 0.10)
                        top10_count = sum(1 for r in ranks if r <= top10_thresh)
                        prob_top10 = (top10_count / n_sims) * 100
                    
                        top1_thresh = int(field_size * 0.01)
                        top1_count = sum(1 for r in ranks if r <= top1_thresh)
                        prob_top1 = (top1_count / n_sims) * 100
                    
                        top01_thresh = int(field_size * 0.001)
                        top01_count = sum(1 for r in ranks if r <= top01_thresh)
                        prob_top01 = (top01_count / n_sims) * 100
                    
                        min_profit = min(profits)
                        max_profit = max(profits)
                    
                        summary_data.append({
                            'Lineup': f"Lineup {i+1}",
                            'Mean Score': f"{mean_score:.2f}",
                            'Mean Profit': f"${mean_profit:.2f}",
                            'ROI': f"{roi:.1f}%",
                            'Cash%': f"{prob_cash:.1f}%",
                            'Top 10%': f"{prob_top10:.1f}%",
                            'Top 1%': f"{prob_top1:.1f}%",
                            'Top 0.1%': f"{prob_top01:.2f}%",
                            'Min Profit': f"${min_profit:.2f}",
                            'Max Profit': f"${max_profit:.2f}"
                        })
                
                    summary_df = pd.DataFrame(summary_data)
                
                    st.subheader("📈 Lineup Summary")
                
                    # Add metric explanations
                    with st.expander("ℹ️ Metric Explanations"):
                        st.markdown("""
                        **Mean Score**: Average fantasy points across all simulations
                    
                        **Mean Profit**: Average profit/loss per entry (payout minus entry fee)
                    
                        **ROI**: Return on Investment = (Mean Profit / Entry Fee) × 100%
                        - Positive ROI = profitable lineup on average
                        - Example: 50% ROI means you earn $1.50 for every $1 entry
                    
                        **Cash%**: Probability of finishing in the money (any positive profit)
                        - 50% = breaks even in long run
                        - >50% = profitable lineup
                    
                        **Top 10%**: Probability of top-10% finish
                        - Measures consistency and upside potential
                        - Important for GPPs with deeper payout structures
                    
                        **Top 1%**: Probability of top-1% finish  
                        - Indicates ceiling/tournament winning potential
                        - Key metric for large-field GPPs
                    
                        **Top 0.1%**: Probability of top-0.1% finish
                        - Elite outcomes (top ~12 in an 11,890-entry field)
                        - Indicates true tournament winner potential
                        - Base rate = 0.1% ({:.0f} positions)
                    
                        **Min/Max Profit**: Range of outcomes across all simulations
                        - Shows best and worst case scenarios
                        - Wide range = high variance lineup
                        """.format(field_size * 0.001))
                
                    st.dataframe(summary_df, use_container_width=True)
                
                    # Download results
                    csv = summary_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results CSV",
                        data=csv,
                        file_name="lineup_sim_results.csv",
                        mime="text/csv"
                    )
                
                    # Detailed view for selected lineup
                    st.subheader("🔍 Detailed Analysis")
                
                    lineup_selection = st.selectbox("Select Lineup", [f"Lineup {i+1}" for i in range(len(user_lineups))])
                    lineup_idx = int(lineup_selection.split()[1]) - 1
                
                    results = sim_results[lineup_idx]
                    scores = [r['score'] for r in results]
                    profits = [r['profit'] for r in results]
                
                    col1, col2 = st.columns(2)
                
                    with col1:
                        st.markdown("**Score Distribution**")
                        score_hist_df = pd.DataFrame({'Score': scores})
                        st.bar_chart(score_hist_df['Score'].value_counts().sort_index(), use_container_width=True)
                
                    with col2:
                        st.markdown("**Profit Distribution**")
                        profit_hist_df = pd.DataFrame({'Profit': profits})
                        st.bar_chart(profit_hist_df['Profit'].value_counts().sort_index(), use_container_width=True)
                
                    # Show actual lineup
                    st.markdown(f"**{lineup_selection} Players:**")
                    lineup_names = user_lineups[lineup_idx]
                    lineup_display = players_df[players_df['Name'].isin(lineup_names)][['Name', 'Position', 'Team', 'Salary', 'median_proj', 'Proj_Own']]
                    st.dataframe(lineup_display, use_container_width=True)
    
        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    else:
        st.info("👆 Please upload all 4 required CSV files to begin simulation")
    
        with st.expander("📖 File Format Requirements"):
            st.markdown("""
            **Players CSV:**
            - Required: Name, Position, Team, Salary
            - Required: median_proj (or projection/proj/fpts)
            - Required: dk_ownership (or ownership/proj_own)
            - Optional: ceiling_proj, var_dk
        
            **Weekly Stats CSV:**
            - Required: Name, Week, DK Points
        
            **Matchup CSV:**
            - Required: Team, Opp, Total
            - Optional: Spread, EPA, YPP, PPD, Explosive, Conv
        
            **Lineups CSV:**
            - Required: QB, RB1, RB2, WR1, WR2, WR3, TE, FLEX, DST
            - Supports DraftKings export format (with player IDs in parentheses)
        
            **Team Plays Offense CSV (Optional):**
            - Required: Team, Avg Plays, Avg Pass Att, Avg Rush Att
            - Required: Avg Pass Yds, Avg Rush Yds, Avg Pass 1stD, Avg Rush 1stD
            - Required: Avg_Rush_TD, Avg_Pass_TD
            - Enhances position-specific scoring adjustments based on team tendencies
        
            **Team Plays Defense CSV (Optional):**
            - Required: Opp, Avg Plays, Avg Pass Att, Avg Rush Att
            - Required: Avg Pass Yds, Avg Rush Yds, Avg Pass 1stD, Avg Rush 1stD
            - Required: Avg_Rush_TD, Avg_Pass_TD
            - Shows what teams allow to opponents (DST scoring adjustments)
        
            **Payout Structure Format:**
            - One line per rank range
            - Format: `start_rank-end_rank:payout_amount`
            - Example: `1-1:1000` (1st place wins $1000)
            - Example: `6-7:125` (6th-7th place each win $125)
            - Example: `411-765:6` (411th-765th place each win $6)
            """)



# Standalone execution
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    run()
