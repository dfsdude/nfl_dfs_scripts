import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import itertools

# st.set_page_config(page_title="Pre-Contest Simulator", layout="wide")

def run():
    """Main entry point for this tool"""
    st.title("🎲 Pre-Contest Simulator")

    st.markdown("""
    **Optimize your player pool and exposures BEFORE lineup lock.** This simulator runs thousands of scenarios
    to identify which players offer the best ROI and what your optimal exposure levels should be.
    """)

    # --------------------------------------------------------
    # File Upload Section
    # --------------------------------------------------------
    st.sidebar.header("📁 Upload Data Files")

    projections_file = st.sidebar.file_uploader(
        "Player Projections",
        type=['csv'],
        help="Upload your boom/bust projections file with: name, position, salary, team, opp, proj_adj, ceiling_adj, stddev_adj (or will be calculated), Own%"
    )

    matchup_file = st.sidebar.file_uploader(
        "Matchup Data (Optional)",
        type=['csv'],
        help="Upload Matchup.csv with game environment and team stats (ITT, Total, Spread, EPA, etc.)"
    )

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Contest Settings")

    contest_size = st.sidebar.number_input("Contest Size", min_value=2, value=4705, step=1)
    entry_fee = st.sidebar.number_input("Entry Fee ($)", min_value=0.0, value=10.0, step=1.0)
    num_lineups = st.sidebar.number_input("Number of Lineups", min_value=1, max_value=150, value=20, step=1,
                                          help="How many lineups will you enter?")

    # Payout structure (same as contest analyzer)
    payout_structure = {
        1: 4000,
        2: 2000,
        3: 1500,
        4: 1000,
        5: 750,
        6: 600,
        (7, 8): 500,
        (9, 10): 400,
        (11, 12): 300,
        (13, 14): 250,
        (15, 19): 200,
        (20, 24): 150,
        (25, 29): 100,
        (30, 39): 75,
        (40, 49): 60,
        (50, 74): 50,
        (75, 124): 40,
        (125, 225): 30,
        (226, 415): 25,
        (416, 1046): 20
    }

    def get_payout(rank):
        """Get payout amount for a given rank"""
        for key, value in payout_structure.items():
            if isinstance(key, tuple):
                if key[0] <= rank <= key[1]:
                    return value
            elif rank == key:
                return value
        return 0

    # --------------------------------------------------------
    # Main Analysis
    # --------------------------------------------------------
    if projections_file:
    
        # Load projections
        projections_df = pd.read_csv(projections_file)
    
        st.success(f"✅ Loaded {len(projections_df)} players")
    
        # Detect and standardize columns
        def find_column(df, possible_names):
            """Find column by checking possible name variations"""
            for col in df.columns:
                col_lower = col.lower().strip()
                for name in possible_names:
                    if name.lower() in col_lower:
                        return col
            return None
    
        # Map columns
        name_col = find_column(projections_df, ['name', 'player'])
        pos_col = find_column(projections_df, ['position', 'pos'])
        salary_col = find_column(projections_df, ['salary', 'sal'])
        team_col = find_column(projections_df, ['team', 'tm'])
        opp_col = find_column(projections_df, ['opp', 'opponent', 'vs'])
        proj_col = find_column(projections_df, ['proj_adj', 'projection', 'proj', 'fpts', 'median_proj', 'median'])
        ceiling_col = find_column(projections_df, ['ceiling_adj', 'ceiling_proj', 'ceiling'])
        own_col = find_column(projections_df, ['own%', 'ownership', 'own', 'dk_ownership'])
    
        # Check for missing required columns
        missing_cols = []
        if not name_col: missing_cols.append("Player/Name")
        if not pos_col: missing_cols.append("Position")
        if not salary_col: missing_cols.append("Salary")
        if not proj_col: missing_cols.append("Projection (median_proj, proj_adj, or proj)")
        if not ceiling_col: missing_cols.append("Ceiling (ceiling_proj or ceiling_adj)")
        if not own_col: missing_cols.append("Ownership (dk_ownership or own%)")
    
        if missing_cols:
            st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
            st.info("Your file should contain: Player, Position, Team, Salary, median_proj (or proj), ceiling_proj (or ceiling), dk_ownership (or own%)")
            st.stop()
    
        # Standardize
        if name_col: projections_df['name'] = projections_df[name_col]
        if pos_col: projections_df['position'] = projections_df[pos_col]
        if salary_col: projections_df['Salary'] = pd.to_numeric(projections_df[salary_col], errors='coerce')
        if team_col: projections_df['team'] = projections_df[team_col]
        if opp_col: projections_df['opp'] = projections_df[opp_col]
        if proj_col: projections_df['proj_adj'] = pd.to_numeric(projections_df[proj_col], errors='coerce')
        if ceiling_col: projections_df['ceiling_adj'] = pd.to_numeric(projections_df[ceiling_col], errors='coerce')
        if own_col:
            # Handle both percentage format (13.25%) and decimal format (0.1325)
            if projections_df[own_col].dtype == object and projections_df[own_col].astype(str).str.contains('%').any():
                projections_df['Own%'] = projections_df[own_col].str.rstrip('%').astype(float)
            else:
                # Convert to percentage if in decimal format (< 1.0)
                own_values = pd.to_numeric(projections_df[own_col], errors='coerce')
                if own_values.max() <= 1.0:
                    projections_df['Own%'] = own_values * 100
                else:
                    projections_df['Own%'] = own_values
    
        # Drop rows with missing critical data
        projections_df = projections_df.dropna(subset=['name', 'position', 'Salary', 'proj_adj', 'ceiling_adj'])
    
        # Calculate stddev if not present
        stddev_col = find_column(projections_df, ['stddev_adj', 'stddev', 'std'])
        if stddev_col:
            projections_df['stddev_adj'] = projections_df[stddev_col]
        else:
            projections_df['stddev_adj'] = (projections_df['ceiling_adj'] - projections_df['proj_adj']) / 2.0
    
        # Calculate floor
        projections_df['floor_adj'] = projections_df['proj_adj'] - (2 * projections_df['stddev_adj'])
        projections_df['floor_adj'] = projections_df['floor_adj'].clip(lower=0)
    
        # ===== LOAD AND MERGE MATCHUP DATA =====
        if matchup_file:
            try:
                matchup_data = pd.read_csv(matchup_file)
            
                # Merge team-level matchup data
                projections_df = projections_df.merge(
                    matchup_data[['Init', 'ITT', 'Loc', 'FavStatus', 'Spread', 'Total', 
                                 'Init_EPA_Play', 'Init_Yards Per Play', 'Init_Points Per Drive',
                                 'Opp_EPA_Play_Allowed', 'Opp_Yards Per Play Allowed', 'Opp_Points Per Drive Allowed']],
                    left_on='team',
                    right_on='Init',
                    how='left'
                )
            
                st.success(f"✅ Loaded matchup data for {matchup_data['Init'].nunique()} teams")
            except Exception as e:
                st.warning(f"⚠️ Could not load matchup data: {str(e)}")
    
        # Display player pool with matchup data if available
        with st.expander("🔍 View Player Pool", expanded=False):
            # Build display columns dynamically based on what's available
            base_cols = ['name', 'position', 'Salary', 'proj_adj', 'ceiling_adj', 'floor_adj', 'Own%']
            optional_cols = []
        
            if 'team' in projections_df.columns:
                base_cols.insert(3, 'team')
            if 'opp' in projections_df.columns:
                base_cols.insert(4, 'opp')
        
            if matchup_file and 'ITT' in projections_df.columns:
                if 'ITT' in projections_df.columns:
                    optional_cols.append('ITT')
                if 'Total' in projections_df.columns:
                    optional_cols.append('Total')
                if 'Spread' in projections_df.columns:
                    optional_cols.append('Spread')
        
            display_cols = base_cols + optional_cols
            display_df = projections_df[display_cols].copy()
        
            # Build format dict dynamically
            format_dict = {
                'Salary': '${:,.0f}',
                'proj_adj': '{:.1f}',
                'ceiling_adj': '{:.1f}',
                'floor_adj': '{:.1f}',
                'Own%': '{:.1f}%'
            }
        
            if 'ITT' in display_cols:
                format_dict['ITT'] = '{:.1f}'
            if 'Total' in display_cols:
                format_dict['Total'] = '{:.1f}'
            if 'Spread' in display_cols:
                format_dict['Spread'] = '{:+.1f}'
        
            st.dataframe(display_df.style.format(format_dict), height=400, use_container_width=True)
    
        # ===== EXPOSURE SETTINGS =====
        st.header("🎯 Exposure Settings")
    
        st.markdown("""
        Set your target exposure for each player. The simulator will build lineups matching these targets
        and evaluate their expected ROI.
        """)
    
        # Quick exposure presets
        col1, col2, col3 = st.columns(3)
    
        with col1:
            if st.button("📊 Equal Weight All"):
                st.session_state['preset'] = 'equal'
        with col2:
            if st.button("📈 Projection-Based"):
                st.session_state['preset'] = 'projection'
        with col3:
            if st.button("🎲 Ownership-Based"):
                st.session_state['preset'] = 'ownership'
    
        # Initialize exposure column
        if 'exposure' not in projections_df.columns:
            projections_df['exposure'] = 0.0
    
        # Apply presets
        if 'preset' in st.session_state:
            if st.session_state['preset'] == 'equal':
                projections_df['exposure'] = 20.0
            elif st.session_state['preset'] == 'projection':
                # Weight by projection percentile
                projections_df['exposure'] = (projections_df['proj_adj'].rank(pct=True) * 50).round(1)
            elif st.session_state['preset'] == 'ownership':
                # Match field ownership
                if 'Own%' in projections_df.columns:
                    projections_df['exposure'] = projections_df['Own%'].fillna(10.0)
    
        # Exposure editor by position
        st.subheader("Edit Exposures by Position")
    
        positions = ['QB', 'RB', 'WR', 'TE', 'DST']
    
        for pos in positions:
            pos_players = projections_df[projections_df['position'] == pos].copy()
        
            if len(pos_players) > 0:
                with st.expander(f"**{pos}** ({len(pos_players)} players)", expanded=False):
                
                    # Create editable dataframe
                    edited_df = st.data_editor(
                        pos_players[['name', 'Salary', 'proj_adj', 'ceiling_adj', 'Own%', 'exposure']],
                        column_config={
                            "name": st.column_config.TextColumn("Player", disabled=True),
                            "Salary": st.column_config.NumberColumn("Salary", format="$%d", disabled=True),
                            "proj_adj": st.column_config.NumberColumn("Projection", format="%.1f", disabled=True),
                            "ceiling_adj": st.column_config.NumberColumn("Ceiling", format="%.1f", disabled=True),
                            "Own%": st.column_config.NumberColumn("Own%", format="%.1f%%", disabled=True),
                            "exposure": st.column_config.NumberColumn("Your Exposure %", min_value=0.0, max_value=100.0, step=5.0, format="%.1f%%")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                
                    # Update main dataframe
                    projections_df.loc[projections_df['position'] == pos, 'exposure'] = edited_df['exposure'].values
    
        # Show exposure summary
        st.markdown("---")
        st.subheader("📊 Exposure Summary")
    
        col1, col2, col3, col4 = st.columns(4)
    
        with col1:
            total_exposure = projections_df['exposure'].sum()
            st.metric("Total Exposure %", f"{total_exposure:.0f}%")
    
        with col2:
            players_with_exposure = len(projections_df[projections_df['exposure'] > 0])
            st.metric("Players with Exposure", players_with_exposure)
    
        with col3:
            avg_exposure = projections_df[projections_df['exposure'] > 0]['exposure'].mean()
            st.metric("Avg Exposure (non-zero)", f"{avg_exposure:.1f}%")
    
        with col4:
            max_exposure_player = projections_df.loc[projections_df['exposure'].idxmax()]
            st.metric("Highest Exposure", f"{max_exposure_player['name']} ({max_exposure_player['exposure']:.0f}%)")
    
        # ===== RUN SIMULATION =====
        st.markdown("---")
        st.header("🚀 Run Simulation")
    
        col1, col2 = st.columns(2)
    
        with col1:
            n_simulations = st.number_input("Number of Simulations", min_value=100, max_value=5000, value=1000, step=100)
    
        with col2:
            run_sim = st.button("▶️ Run Pre-Contest Simulation", type="primary", use_container_width=True)
    
        if run_sim:
        
            # Validate exposures
            players_with_exp = projections_df[projections_df['exposure'] > 0]
        
            if len(players_with_exp) < 9:
                st.error("❌ Need at least 9 players with exposure to build lineups (1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX, 1 DST)")
                st.stop()
        
            with st.spinner(f"Running {n_simulations:,} simulations with {num_lineups} lineups each..."):
            
                # Create player stats mapping
                player_stats = {}
                for _, row in projections_df.iterrows():
                    player_stats[row['name']] = {
                        'mean': row['proj_adj'],
                        'std': row['stddev_adj'],
                        'floor': row['floor_adj'],
                        'ceiling': row['ceiling_adj'],
                        'salary': row['Salary'],
                        'position': row['position'],
                        'exposure': row['exposure'],
                        'ownership': row.get('Own%', 10.0)
                    }
            
                # Generate lineups based on exposures (simplified - random selection weighted by exposure)
                my_lineups = []
            
                np.random.seed(42)
            
                for lineup_num in range(num_lineups):
                    lineup = []
                    remaining_salary = 50000
                
                    # Build lineup by position
                    for pos in ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'DST']:
                        pos_players = projections_df[
                            (projections_df['position'] == pos) & 
                            (projections_df['exposure'] > 0) &
                            (projections_df['Salary'] <= remaining_salary)
                        ].copy()
                    
                        if len(pos_players) == 0:
                            continue
                    
                        # Weight by exposure
                        weights = pos_players['exposure'].values
                        weights = weights / weights.sum()
                    
                        selected_player = np.random.choice(pos_players['name'].values, p=weights)
                        lineup.append(selected_player)
                        remaining_salary -= pos_players[pos_players['name'] == selected_player]['Salary'].iloc[0]
                
                    # Add FLEX (RB/WR/TE)
                    flex_players = projections_df[
                        (projections_df['position'].isin(['RB', 'WR', 'TE'])) &
                        (projections_df['exposure'] > 0) &
                        (projections_df['Salary'] <= remaining_salary)
                    ].copy()
                
                    if len(flex_players) > 0:
                        weights = flex_players['exposure'].values
                        weights = weights / weights.sum()
                        selected_player = np.random.choice(flex_players['name'].values, p=weights)
                        lineup.append(selected_player)
                
                    my_lineups.append(lineup)
            
                # Generate field lineups (ownership-based)
                field_lineups = []
                field_sample_size = min(1000, contest_size - num_lineups)
            
                for lineup_num in range(field_sample_size):
                    lineup = []
                    remaining_salary = 50000
                
                    for pos in ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'DST']:
                        pos_players = projections_df[
                            (projections_df['position'] == pos) &
                            (projections_df['Salary'] <= remaining_salary)
                        ].copy()
                    
                        if len(pos_players) == 0:
                            continue
                    
                        # Weight by ownership
                        weights = pos_players['Own%'].fillna(5.0).values
                        weights = weights / weights.sum()
                    
                        selected_player = np.random.choice(pos_players['name'].values, p=weights)
                        lineup.append(selected_player)
                        remaining_salary -= pos_players[pos_players['name'] == selected_player]['Salary'].iloc[0]
                
                    # Add FLEX
                    flex_players = projections_df[
                        (projections_df['position'].isin(['RB', 'WR', 'TE'])) &
                        (projections_df['Salary'] <= remaining_salary)
                    ].copy()
                
                    if len(flex_players) > 0:
                        weights = flex_players['Own%'].fillna(5.0).values
                        weights = weights / weights.sum()
                        selected_player = np.random.choice(flex_players['name'].values, p=weights)
                        lineup.append(selected_player)
                
                    field_lineups.append(lineup)
            
                all_lineups = []
                for i, lineup in enumerate(my_lineups):
                    all_lineups.append({'lineup': lineup, 'is_mine': True, 'entry_name': f'My Lineup {i+1}'})
                for i, lineup in enumerate(field_lineups):
                    all_lineups.append({'lineup': lineup, 'is_mine': False, 'entry_name': f'Field {i+1}'})
            
                st.info(f"📊 Generated {len(my_lineups)} of your lineups and {len(field_lineups)} field lineups")
            
                # Run simulations
                progress_bar = st.progress(0)
                lineup_sim_scores = {i: [] for i in range(len(all_lineups))}
            
                for sim_num in range(n_simulations):
                    # Generate simulated scores for all players
                    sim_player_scores = {}
                
                    for player_name, stats in player_stats.items():
                        score = np.random.normal(stats['mean'], stats['std'])
                        score = max(stats['floor'], min(stats['ceiling'], score))
                        sim_player_scores[player_name] = score
                
                    # Score each lineup
                    for lineup_idx, lineup_data in enumerate(all_lineups):
                        lineup_score = sum(sim_player_scores.get(p, 0) for p in lineup_data['lineup'])
                        lineup_sim_scores[lineup_idx].append(lineup_score)
                
                    if sim_num % 100 == 0:
                        progress_bar.progress((sim_num + 1) / n_simulations)
            
                progress_bar.progress(1.0)
                st.success(f"✅ Completed {n_simulations:,} simulations!")
            
                # ===== ANALYZE RESULTS =====
                st.markdown("---")
                st.header("📈 Simulation Results")
            
                # Calculate metrics
                lineup_results = []
            
                for lineup_idx, lineup_data in enumerate(all_lineups):
                    sim_scores = lineup_sim_scores[lineup_idx]
                    avg_finishes = []
                    total_winnings = 0
                
                    for sim_num in range(n_simulations):
                        all_sim_scores = [lineup_sim_scores[i][sim_num] for i in range(len(all_lineups))]
                        lineup_score = sim_scores[sim_num]
                        sample_rank = sum(1 for score in all_sim_scores if score > lineup_score) + 1
                        percentile = sample_rank / len(all_lineups)
                        estimated_rank = int(percentile * contest_size)
                        estimated_rank = max(1, min(contest_size, estimated_rank))
                        avg_finishes.append(estimated_rank)
                        payout = get_payout(estimated_rank)
                        total_winnings += payout
                
                    avg_finish = np.mean(avg_finishes)
                    avg_winnings = total_winnings / n_simulations
                    sim_roi = ((avg_winnings - entry_fee) / entry_fee) * 100 if entry_fee > 0 else 0
                
                    lineup_results.append({
                        'Entry_Name': lineup_data['entry_name'],
                        'Is_Mine': lineup_data['is_mine'],
                        'Sim_Avg_Points': np.mean(sim_scores),
                        'Sim_Avg_Finish': avg_finish,
                        'Sim_Avg_Winnings': avg_winnings,
                        'Sim_ROI': sim_roi,
                        'Players': lineup_data['lineup']
                    })
            
                results_df = pd.DataFrame(lineup_results)
            
                # Portfolio analysis
                my_results = results_df[results_df['Is_Mine'] == True]
                field_results = results_df[results_df['Is_Mine'] == False]
            
                st.subheader("💼 Your Portfolio Performance")
            
                col1, col2, col3, col4 = st.columns(4)
            
                with col1:
                    my_avg_roi = my_results['Sim_ROI'].mean()
                    field_avg_roi = field_results['Sim_ROI'].mean()
                    delta = my_avg_roi - field_avg_roi
                    st.metric("Expected Avg ROI", f"{my_avg_roi:.1f}%", delta=f"{delta:+.1f}% vs Field")
            
                with col2:
                    my_avg_proj = my_results['Sim_Avg_Points'].mean()
                    field_avg_proj = field_results['Sim_Avg_Points'].mean()
                    delta = my_avg_proj - field_avg_proj
                    st.metric("Avg Projected Points", f"{my_avg_proj:.1f}", delta=f"{delta:+.1f} vs Field")
            
                with col3:
                    total_invested = num_lineups * entry_fee
                    total_exp_winnings = my_results['Sim_Avg_Winnings'].sum()
                    portfolio_roi = ((total_exp_winnings - total_invested) / total_invested) * 100 if total_invested > 0 else 0
                    st.metric("Portfolio ROI", f"{portfolio_roi:.1f}%")
            
                with col4:
                    net_profit = total_exp_winnings - total_invested
                    st.metric("Expected Profit", f"${net_profit:.2f}")
            
                # Player ROI Analysis
                st.markdown("---")
                st.subheader("🎯 Player Sim ROI Analysis")
            
                player_roi_data = {}
            
                for _, lineup in my_results.iterrows():
                    for player in lineup['Players']:
                        if player not in player_roi_data:
                            player_roi_data[player] = {'lineups': 0, 'total_roi': 0}
                        player_roi_data[player]['lineups'] += 1
                        player_roi_data[player]['total_roi'] += lineup['Sim_ROI']
            
                player_roi_list = []
                for player, data in player_roi_data.items():
                    player_info = projections_df[projections_df['name'] == player]
                    if not player_info.empty:
                        avg_roi = data['total_roi'] / data['lineups']
                        my_exp = (data['lineups'] / len(my_results)) * 100
                        target_exp = player_info.iloc[0]['exposure']
                        field_own = player_info.iloc[0].get('Own%', 0)
                    
                        player_roi_list.append({
                            'Player': player,
                            'Position': player_info.iloc[0]['position'],
                            'Salary': player_info.iloc[0]['Salary'],
                            'Sim_Player_ROI': avg_roi,
                            'Target_Exp%': target_exp,
                            'Actual_Exp%': my_exp,
                            'Field_Own%': field_own,
                            'Proj': player_info.iloc[0]['proj_adj'],
                            'Ceiling': player_info.iloc[0]['ceiling_adj']
                        })
            
                player_roi_df = pd.DataFrame(player_roi_list)
                player_roi_df = player_roi_df.sort_values('Sim_Player_ROI', ascending=False)
            
                # Display top players
                col1, col2 = st.columns(2)
            
                with col1:
                    st.markdown("#### ⭐ Highest Sim Player ROI")
                    top_players = player_roi_df.head(15)
                    st.dataframe(
                        top_players[['Player', 'Position', 'Sim_Player_ROI', 'Actual_Exp%', 'Field_Own%']].style.format({
                            'Sim_Player_ROI': '{:.1f}%',
                            'Actual_Exp%': '{:.1f}%',
                            'Field_Own%': '{:.1f}%'
                        }).background_gradient(subset=['Sim_Player_ROI'], cmap='Greens'),
                        use_container_width=True
                    )
            
                with col2:
                    st.markdown("#### 💔 Lowest Sim Player ROI")
                    bottom_players = player_roi_df.tail(15)
                    st.dataframe(
                        bottom_players[['Player', 'Position', 'Sim_Player_ROI', 'Actual_Exp%', 'Field_Own%']].style.format({
                            'Sim_Player_ROI': '{:.1f}%',
                            'Actual_Exp%': '{:.1f}%',
                            'Field_Own%': '{:.1f}%'
                        }).background_gradient(subset=['Sim_Player_ROI'], cmap='Reds_r'),
                        use_container_width=True
                    )
            
                # Exposure optimization suggestions
                st.markdown("---")
                st.subheader("💡 Exposure Optimization Suggestions")
            
                st.markdown("""
                Based on Sim Player ROI, here are recommended exposure adjustments:
                """)
            
                # High ROI, low exposure (increase these)
                increase_candidates = player_roi_df[
                    (player_roi_df['Sim_Player_ROI'] > 15) &
                    (player_roi_df['Actual_Exp%'] < player_roi_df['Actual_Exp%'].quantile(0.5))
                ].head(10)
            
                if not increase_candidates.empty:
                    st.markdown("**📈 Increase Exposure:**")
                    for _, row in increase_candidates.iterrows():
                        st.write(f"- **{row['Player']}** ({row['Position']}): {row['Sim_Player_ROI']:.1f}% ROI, "
                                f"Currently {row['Actual_Exp%']:.0f}% → Suggest {min(row['Actual_Exp%'] + 20, 60):.0f}%")
            
                # Low ROI, high exposure (decrease these)
                decrease_candidates = player_roi_df[
                    (player_roi_df['Sim_Player_ROI'] < 5) &
                    (player_roi_df['Actual_Exp%'] > player_roi_df['Actual_Exp%'].quantile(0.5))
                ].head(10)
            
                if not decrease_candidates.empty:
                    st.markdown("**📉 Decrease Exposure:**")
                    for _, row in decrease_candidates.iterrows():
                        st.write(f"- **{row['Player']}** ({row['Position']}): {row['Sim_Player_ROI']:.1f}% ROI, "
                                f"Currently {row['Actual_Exp%']:.0f}% → Suggest {max(row['Actual_Exp%'] - 15, 0):.0f}%")
            
                # Download optimized exposures
                st.markdown("---")
                optimized_exposures = player_roi_df[['Player', 'Position', 'Salary', 'Sim_Player_ROI', 
                                                     'Target_Exp%', 'Actual_Exp%', 'Field_Own%']]
            
                csv = optimized_exposures.to_csv(index=False)
                st.download_button(
                    label="📥 Download Player ROI Report",
                    data=csv,
                    file_name="player_sim_roi_report.csv",
                    mime="text/csv"
                )

    else:
        st.info("👈 Upload your projections file to begin")
    
        st.markdown("""
        ### Expected File Format:
    
        **Player Projections CSV:**
        - Required columns: `name`, `position`, `Salary`, `proj_adj`, `ceiling_adj`
        - Optional columns: `team`, `opp`, `stddev_adj` (will calculate if missing), `Own%`
    
        ### How to Use:
    
        1. **Upload Projections**: Your boom/bust file with player stats
        2. **Set Contest Settings**: Size, entry fee, number of lineups
        3. **Configure Exposures**: Set target % for each player
        4. **Run Simulation**: See expected ROI for each player
        5. **Optimize**: Adjust exposures based on Sim Player ROI results
        6. **Export**: Download optimized exposures for your lineup builder
        """)


# Standalone execution
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    run()
