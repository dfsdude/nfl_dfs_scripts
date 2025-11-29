import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import itertools

st.set_page_config(page_title="DFS Contest Analyzer", layout="wide")
st.title("🏆 DFS Contest Analyzer")

# --------------------------------------------------------
# File Upload Section
# --------------------------------------------------------
st.sidebar.header("📁 Upload Contest Data")

ownership_file = st.sidebar.file_uploader(
    "1. Player Ownership & FPTS", 
    type=['csv'],
    help="Player ownership percentages and actual DK points scored"
)

winners_file = st.sidebar.file_uploader(
    "2. Contest Top 0.1%", 
    type=['csv'],
    help="Top finishing lineups from the tournament"
)

my_entries_file = st.sidebar.file_uploader(
    "3. My Entries", 
    type=['csv'],
    help="Your tournament entries with scores"
)

boom_bust_file = st.sidebar.file_uploader(
    "4. Player Boom/Bust Projections", 
    type=['csv'],
    help="Pre-contest boom/bust probabilities and projections"
)

# --------------------------------------------------------
# Load and Process Data
# --------------------------------------------------------
if all([ownership_file, winners_file, my_entries_file, boom_bust_file]):
    
    # Load data
    ownership_df = pd.read_csv(ownership_file)
    winners_df = pd.read_csv(winners_file)
    my_entries_df = pd.read_csv(my_entries_file)
    boom_bust_df = pd.read_csv(boom_bust_file)
    
    st.success("✅ All files loaded successfully!")
    
    # --------------------------------------------------------
    # Data Processing
    # --------------------------------------------------------
    
    # Detect column names dynamically
    def find_column(df, possible_names):
        """Find column by checking possible name variations"""
        for col in df.columns:
            col_lower = col.lower().strip()
            for name in possible_names:
                if name.lower() in col_lower:
                    return col
        return None
    
    # Map column names for ownership file
    name_col = find_column(ownership_df, ['player', 'name', 'player name'])
    own_col = find_column(ownership_df, ['%drafted', 'drafted', 'own%', 'ownership'])
    fpts_col = find_column(ownership_df, ['fpts', 'points', 'dk points'])
    salary_col = find_column(ownership_df, ['salary', 'sal'])
    position_col = find_column(ownership_df, ['roster position', 'position', 'pos'])
    
    # Debug: Show column names
    with st.expander("🔍 Debug: Column Names", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write("**Ownership:**", list(ownership_df.columns))
            st.write(f"✓ name: `{name_col}`")
            st.write(f"✓ own%: `{own_col}`")
            st.write(f"✓ fpts: `{fpts_col}`")
        with col2:
            st.write("**Winners:**", list(winners_df.columns))
        with col3:
            st.write("**My Entries:**", list(my_entries_df.columns))
        with col4:
            st.write("**Boom/Bust:**", list(boom_bust_df.columns))
    
    # Standardize column names only if found
    if name_col and name_col != 'name': 
        ownership_df['name'] = ownership_df[name_col]
    elif not name_col:
        st.error("❌ Could not find player name column in ownership file")
        st.stop()
    
    if own_col and own_col != 'Own%':
        # Handle percentage strings (e.g., '44.31%')
        if ownership_df[own_col].dtype == object:
            ownership_df['Own%'] = ownership_df[own_col].str.rstrip('%').astype(float)
        else:
            ownership_df['Own%'] = ownership_df[own_col]
    elif not own_col:
        st.warning("⚠️ Could not find ownership column - some features may not work")
    
    if fpts_col and fpts_col != 'FPTS': 
        ownership_df['FPTS'] = ownership_df[fpts_col]
    elif not fpts_col:
        st.error("❌ Could not find FPTS/points column in ownership file")
        st.stop()
    
    if salary_col and salary_col != 'Salary': 
        ownership_df['Salary'] = ownership_df[salary_col]
    
    if position_col and position_col != 'position': 
        ownership_df['position'] = ownership_df[position_col]
    
    # Map column names for boom/bust file
    boom_name_col = find_column(boom_bust_df, ['name', 'player', 'player name'])
    if boom_name_col and boom_name_col != 'name':
        boom_bust_df['name'] = boom_bust_df[boom_name_col]
    
    boom_team_col = find_column(boom_bust_df, ['team', 'tm', 'team name'])
    if boom_team_col and boom_team_col != 'team':
        boom_bust_df['team'] = boom_bust_df[boom_team_col]
    
    boom_opp_col = find_column(boom_bust_df, ['opp', 'opponent', 'vs'])
    if boom_opp_col and boom_opp_col != 'opp':
        boom_bust_df['opp'] = boom_bust_df[boom_opp_col]
    
    # Merge salary, position, team, and opponent data from boom/bust into ownership
    if 'name' in boom_bust_df.columns and 'name' in ownership_df.columns:
        # Select columns to merge from boom/bust
        merge_cols = ['name']
        if 'Salary' in boom_bust_df.columns and 'Salary' not in ownership_df.columns:
            merge_cols.append('Salary')
        if 'position' in boom_bust_df.columns and 'position' not in ownership_df.columns:
            merge_cols.append('position')
        if 'team' in boom_bust_df.columns:
            merge_cols.append('team')
        if 'opp' in boom_bust_df.columns:
            merge_cols.append('opp')
        
        if len(merge_cols) > 1:
            ownership_df = ownership_df.merge(
                boom_bust_df[merge_cols],
                on='name',
                how='left'
            )
    
    # Detect lineup column (might be 'Lineup', 'lineup', or similar)
    lineup_col = find_column(winners_df, ['lineup'])
    
    if not lineup_col:
        st.error("❌ Could not find 'Lineup' column in winners file. Please check column names.")
        st.stop()
    
    # Extract player names from lineup strings
    def parse_lineup(lineup_str):
        """Extract player names from lineup string"""
        if pd.isna(lineup_str):
            return []
        
        players = []
        parts = str(lineup_str).split()
        
        # Skip position labels (DST, FLEX, QB, RB, TE, WR)
        positions = ['DST', 'FLEX', 'QB', 'RB', 'TE', 'WR']
        current_name = []
        
        for part in parts:
            if part in positions:
                if current_name:
                    players.append(' '.join(current_name))
                    current_name = []
            else:
                current_name.append(part)
        
        if current_name:
            players.append(' '.join(current_name))
        
        return players
    
    def parse_lineup_with_positions(lineup_str):
        """Extract player names with their positions from lineup string"""
        if pd.isna(lineup_str):
            return []
        
        lineup = []
        parts = str(lineup_str).split()
        
        positions = ['DST', 'FLEX', 'QB', 'RB', 'TE', 'WR']
        current_position = None
        current_name = []
        
        for part in parts:
            if part in positions:
                if current_name and current_position:
                    lineup.append({'position': current_position, 'name': ' '.join(current_name)})
                current_position = part
                current_name = []
            else:
                current_name.append(part)
        
        if current_name and current_position:
            lineup.append({'position': current_position, 'name': ' '.join(current_name)})
        
        return lineup
    
    # Parse all lineups
    winners_df['players_list'] = winners_df[lineup_col].apply(parse_lineup)
    my_entries_df['players_list'] = my_entries_df[lineup_col].apply(parse_lineup)
    
    # --------------------------------------------------------
    # Pre-calculate common data used across tabs
    # --------------------------------------------------------
    
    # Get all players from top 0.1%
    winner_players = []
    for players_list in winners_df['players_list']:
        winner_players.extend(players_list)
    
    winner_player_counts = Counter(winner_players)
    total_winners = len(winners_df)
    
    # Get all players from my entries
    my_all_players = []
    for players_list in my_entries_df['players_list']:
        my_all_players.extend(players_list)
    
    my_player_counts = Counter(my_all_players)
    
    # --------------------------------------------------------
    # Analysis Sections
    # --------------------------------------------------------
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Ownership Analysis",
        "🎯 Leverage Report", 
        "🧱 Stack Analysis",
        "📈 My Performance",
        "🔬 Boom/Bust Accuracy",
        "💰 ROI Tracker",
        "🎲 Post-Contest Simulator"
    ])
    
    # --------------------------------------------------------
    # TAB 1: Ownership Analysis
    # --------------------------------------------------------
    with tab1:
        st.header("📊 Ownership Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Field Ownership Distribution")
            
            # Merge ownership with actual points
            if 'name' in ownership_df.columns and 'Own%' in ownership_df.columns and 'FPTS' in ownership_df.columns:
                own_stats = ownership_df[['name', 'Own%', 'FPTS']].copy()
                own_stats = own_stats.sort_values('Own%', ascending=False).head(20)
                
                st.dataframe(
                    own_stats.style.format({'Own%': '{:.1f}%', 'FPTS': '{:.1f}'}),
                    width='stretch'
                )
            else:
                st.warning("⚠️ Missing required columns: name, Own%, or FPTS")
        
        with col2:
            st.subheader("Top Scorer Ownership")
            
            # Top 10 scorers and their ownership
            if 'FPTS' in ownership_df.columns and 'name' in ownership_df.columns and 'Own%' in ownership_df.columns:
                top_scorers = ownership_df.nlargest(10, 'FPTS')[['name', 'FPTS', 'Own%']]
                
                st.dataframe(
                    top_scorers.style.format({'Own%': '{:.1f}%', 'FPTS': '{:.1f}'}),
                    width='stretch'
                )
            else:
                st.warning("⚠️ Missing required columns for top scorers analysis")
        
        # Ownership vs Performance Scatter
        st.subheader("Ownership vs Performance")
        
        if 'Own%' in ownership_df.columns and 'FPTS' in ownership_df.columns:
            # Create interactive scatter plot
            fig = px.scatter(
                ownership_df,
                x='Own%',
                y='FPTS',
                color='FPTS',
                hover_data=['name', 'position'] if 'position' in ownership_df.columns else ['name'],
                color_continuous_scale='RdYlGn',
                title='Player Ownership vs Actual Performance',
                labels={'Own%': 'Ownership %', 'FPTS': 'Fantasy Points'}
            )
            
            fig.update_traces(marker=dict(size=10, opacity=0.7))
            fig.update_layout(height=600, hovermode='closest')
            
            st.plotly_chart(fig, width='stretch')
    
    # --------------------------------------------------------
    # TAB 2: Leverage Report
    # --------------------------------------------------------
    with tab2:
        st.header("🎯 Leverage Report")
        
        st.markdown("""
        **Leverage** = Players who performed well but were under-owned
        
        Top winners likely had these low-owned, high-scoring plays
        """)
        
        # Calculate leverage scores
        if 'Own%' in ownership_df.columns and 'FPTS' in ownership_df.columns:
            leverage_df = ownership_df.copy()
            
            # Leverage = (FPTS - avg_FPTS) / Own%
            avg_fpts = leverage_df['FPTS'].mean()
            leverage_df['Leverage_Score'] = (leverage_df['FPTS'] - avg_fpts) / (leverage_df['Own%'] + 1)
            leverage_df['FPTS_vs_Avg'] = leverage_df['FPTS'] - avg_fpts
            
            # Top leverage plays (high scoring, low owned)
            st.subheader("🔥 Top Leverage Plays")
            
            # Build display columns based on what's available
            display_cols = ['name']
            if 'position' in leverage_df.columns:
                display_cols.append('position')
            if 'Salary' in leverage_df.columns:
                display_cols.append('Salary')
            display_cols.extend(['Own%', 'FPTS', 'FPTS_vs_Avg', 'Leverage_Score'])
            
            top_leverage = leverage_df.nlargest(15, 'Leverage_Score')[display_cols]
            
            # Format display
            format_dict = {
                'Own%': '{:.1f}%',
                'FPTS': '{:.1f}',
                'FPTS_vs_Avg': '{:.1f}',
                'Leverage_Score': '{:.2f}'
            }
            if 'Salary' in display_cols:
                format_dict['Salary'] = '${:,.0f}'
            
            st.dataframe(
                top_leverage.style
                .format(format_dict)
                .background_gradient(subset=['Leverage_Score'], cmap='Greens'),
                width='stretch'
            )
            
            # Winners' unique players
            st.subheader("🏆 Winners' Edge Players")
            
            # Calculate winner ownership
            winner_own_df = pd.DataFrame([
                {'Player': player, 'Winner_Own%': (count/total_winners)*100}
                for player, count in winner_player_counts.most_common()
            ])
            
            # Merge with field ownership
            if 'name' in ownership_df.columns:
                comparison_df = ownership_df[['name', 'Own%', 'FPTS']].merge(
                    winner_own_df,
                    left_on='name',
                    right_on='Player',
                    how='inner'
                )
                
                comparison_df['Own_Diff'] = comparison_df['Winner_Own%'] - comparison_df['Own%']
                
                # Players over-represented in winning lineups
                edge_players = comparison_df.nlargest(15, 'Own_Diff')[
                    ['name', 'Own%', 'Winner_Own%', 'Own_Diff', 'FPTS']
                ]
                
                st.dataframe(
                    edge_players.style
                    .format({
                        'Own%': '{:.1f}%',
                        'Winner_Own%': '{:.1f}%',
                        'Own_Diff': '{:.1f}%',
                        'FPTS': '{:.1f}'
                    })
                    .background_gradient(subset=['Own_Diff'], cmap='Blues'),
                    width='stretch'
                )
    
    # --------------------------------------------------------
    # TAB 3: Stack Analysis
    # --------------------------------------------------------
    with tab3:
        st.header("🧱 Stack Analysis")
        
        # Create player lookup with team info
        player_team_map = {}
        player_pos_map = {}
        player_opp_map = {}
        if 'name' in ownership_df.columns:
            if 'team' in ownership_df.columns:
                player_team_map = dict(zip(ownership_df['name'], ownership_df['team']))
            if 'position' in ownership_df.columns:
                player_pos_map = dict(zip(ownership_df['name'], ownership_df['position']))
            if 'opp' in ownership_df.columns:
                player_opp_map = dict(zip(ownership_df['name'], ownership_df['opp']))
        
        # Parse all winning lineups with positions
        winning_lineups = []
        for _, row in winners_df.iterrows():
            lineup_data = parse_lineup_with_positions(row[lineup_col])
            winning_lineups.append(lineup_data)
        
        # ===== QB Stack Analysis =====
        st.subheader("🏈 Quarterback Stack Distribution")
        
        qb_stack_analysis = []
        secondary_stacks = []
        bring_back_count = 0
        secondary_game_stack_count = 0
        
        for lineup in winning_lineups:
            # Find QB and their team
            qb_name = None
            qb_team = None
            qb_opp = None
            
            for player in lineup:
                if player['position'] == 'QB':
                    qb_name = player['name']
                    qb_team = player_team_map.get(qb_name)
                    qb_opp = player_opp_map.get(qb_name)
                    break
            
            if qb_name and qb_team:
                # Count teammates with QB (same team, pass catchers)
                qb_teammates = []
                bring_back_players = []
                game_teams = {qb_team}  # Track all games represented
                if qb_opp:
                    game_teams.add(qb_opp)
                
                # Track players by team/game
                team_players = {}  # team -> list of (player, pos)
                
                for player in lineup:
                    player_name = player['name']
                    player_team = player_team_map.get(player_name)
                    player_opp = player_opp_map.get(player_name)
                    player_pos = player_pos_map.get(player_name, player['position'])
                    
                    if player_name != qb_name and player_team and player_pos in ['WR', 'TE', 'RB']:
                        # Track by team
                        if player_team not in team_players:
                            team_players[player_team] = []
                        team_players[player_team].append((player_name, player_pos))
                        
                        if player_team == qb_team:
                            # QB teammate (primary stack)
                            qb_teammates.append(player_name)
                        elif qb_opp and player_team == qb_opp:
                            # Bring-back: opponent's pass catcher in same game
                            bring_back_players.append(player_name)
                            game_teams.add(player_team)
                            if player_opp:
                                game_teams.add(player_opp)
                        else:
                            # Different game
                            if player_opp:
                                game_teams.add(player_team)
                                game_teams.add(player_opp)
                
                # Classify QB stack size
                teammate_count = len(qb_teammates)
                
                if teammate_count == 0:
                    stack_type = "QB Only"
                elif teammate_count == 1:
                    stack_type = "QB+1"
                elif teammate_count == 2:
                    stack_type = "QB+2"
                else:
                    stack_type = "QB+3"
                
                # Check for bring-back
                has_bringback = len(bring_back_players) > 0
                if has_bringback:
                    bring_back_count += 1
                
                # Check for secondary game stacks (2+ players from a different game)
                has_secondary_game_stack = False
                secondary_stack_details = []
                
                for team, players in team_players.items():
                    if team != qb_team and team != qb_opp and len(players) >= 2:
                        # This is a secondary stack from a different game
                        has_secondary_game_stack = True
                        secondary_stack_details.append(f"{team} ({len(players)})")
                        secondary_stacks.append(f"{team} Stack ({len(players)} players)")
                
                if has_secondary_game_stack:
                    secondary_game_stack_count += 1
                
                qb_stack_analysis.append({
                    'Stack_Type': stack_type,
                    'Bring_Back': 'Yes' if has_bringback else 'No',
                    'Secondary_Game_Stack': 'Yes' if has_secondary_game_stack else 'No',
                    'QB': qb_name,
                    'Teammates': teammate_count,
                    'Total_Games': len(game_teams)
                })
            else:
                # No team data available
                qb_stack_analysis.append({
                    'Stack_Type': 'Unknown',
                    'Bring_Back': 'Unknown',
                    'Secondary_Game_Stack': 'Unknown',
                    'QB': qb_name or 'Unknown',
                    'Teammates': 0,
                    'Total_Games': 0
                })
        
        # Display QB stack distribution
        if qb_stack_analysis:
            qb_stack_df = pd.DataFrame(qb_stack_analysis)
            stack_dist = qb_stack_df['Stack_Type'].value_counts().reset_index()
            stack_dist.columns = ['Stack_Type', 'Count']
            stack_dist['Percentage'] = (stack_dist['Count'] / len(qb_stack_analysis)) * 100
            stack_dist = stack_dist.sort_values('Count', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(
                    stack_dist.style.format({'Percentage': '{:.1f}%'}),
                    width='stretch'
                )
            
            with col2:
                fig = px.pie(
                    stack_dist,
                    values='Count',
                    names='Stack_Type',
                    title='QB Stack Distribution',
                    hole=0.4
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, width='stretch')
            
            # Bring-back analysis
            st.markdown("#### Bring-Back Usage")
            bringback_pct = (bring_back_count / len(winning_lineups)) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Lineups with Bring-Back", f"{bring_back_count} / {len(winning_lineups)}")
            with col2:
                st.metric("Bring-Back %", f"{bringback_pct:.1f}%")
            with col3:
                secondary_pct = (secondary_game_stack_count / len(winning_lineups)) * 100
                st.metric("Secondary Game Stack %", f"{secondary_pct:.1f}%")
            
            st.markdown("---")
            
            # Detailed breakdown
            st.markdown("#### Stack Construction Breakdown")
            
            bring_back_dist = qb_stack_df['Bring_Back'].value_counts().reset_index()
            bring_back_dist.columns = ['Has_Bring_Back', 'Count']
            bring_back_dist['Percentage'] = (bring_back_dist['Count'] / len(qb_stack_analysis)) * 100
            
            secondary_dist = qb_stack_df['Secondary_Game_Stack'].value_counts().reset_index()
            secondary_dist.columns = ['Has_Secondary_Stack', 'Count']
            secondary_dist['Percentage'] = (secondary_dist['Count'] / len(qb_stack_analysis)) * 100
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Bring-Back Distribution**")
                st.dataframe(
                    bring_back_dist.style.format({'Percentage': '{:.1f}%'}),
                    width='stretch'
                )
            with col2:
                st.markdown("**Secondary Game Stack Distribution**")
                st.dataframe(
                    secondary_dist.style.format({'Percentage': '{:.1f}%'}),
                    width='stretch'
                )
        
        # ===== Secondary Stacks =====
        st.subheader("🔄 Secondary Game Stack Analysis")
        
        st.markdown("""
        **Secondary Game Stacks** are 2+ players from the same team in a *different* game than the primary QB stack.
        This strategy diversifies game exposure and captures scoring from multiple contests.
        """)
        
        if secondary_stacks:
            st.metric("Total Secondary Game Stacks", f"{len(secondary_stacks)} instances across {secondary_game_stack_count} lineups ({(secondary_game_stack_count/len(winning_lineups)*100):.1f}%)")
            
            secondary_df = pd.DataFrame({'Stack': secondary_stacks})
            secondary_dist = secondary_df['Stack'].value_counts().reset_index()
            secondary_dist.columns = ['Team_Stack', 'Count']
            secondary_dist['Percentage'] = (secondary_dist['Count'] / len(winning_lineups)) * 100
            
            st.dataframe(
                secondary_dist.head(15).style.format({'Percentage': '{:.1f}%'}),
                width='stretch'
            )
        else:
            st.info("No secondary game stacks detected (requires 2+ players from same team in a different game than QB)")
        
        st.markdown("---")
        
        # ===== MY STACK ANALYSIS =====
        st.subheader("📊 My Stack Construction")
        
        # Parse my lineups
        my_lineups = []
        for _, row in my_entries_df.iterrows():
            lineup_data = parse_lineup_with_positions(row[lineup_col])
            my_lineups.append({
                'lineup': lineup_data,
                'rank': row.get('Rank', None),
                'points': row.get('Points', None),
                'entry_name': row.get('EntryName', 'Entry')
            })
        
        my_qb_stack_analysis = []
        my_secondary_stacks = []
        my_bring_back_count = 0
        my_secondary_game_stack_count = 0
        
        for entry in my_lineups:
            lineup = entry['lineup']
            
            # Find QB and their team
            qb_name = None
            qb_team = None
            qb_opp = None
            
            for player in lineup:
                if player['position'] == 'QB':
                    qb_name = player['name']
                    qb_team = player_team_map.get(qb_name)
                    qb_opp = player_opp_map.get(qb_name)
                    break
            
            if qb_name and qb_team:
                # Count teammates with QB (same team, pass catchers)
                qb_teammates = []
                bring_back_players = []
                game_teams = {qb_team}
                if qb_opp:
                    game_teams.add(qb_opp)
                
                # Track players by team/game
                team_players = {}
                
                for player in lineup:
                    player_name = player['name']
                    player_team = player_team_map.get(player_name)
                    player_opp = player_opp_map.get(player_name)
                    player_pos = player_pos_map.get(player_name, player['position'])
                    
                    if player_name != qb_name and player_team and player_pos in ['WR', 'TE', 'RB']:
                        if player_team not in team_players:
                            team_players[player_team] = []
                        team_players[player_team].append((player_name, player_pos))
                        
                        if player_team == qb_team:
                            qb_teammates.append(player_name)
                        elif qb_opp and player_team == qb_opp:
                            bring_back_players.append(player_name)
                            game_teams.add(player_team)
                            if player_opp:
                                game_teams.add(player_opp)
                        else:
                            if player_opp:
                                game_teams.add(player_team)
                                game_teams.add(player_opp)
                
                # Classify QB stack size
                teammate_count = len(qb_teammates)
                
                if teammate_count == 0:
                    stack_type = "QB Only"
                elif teammate_count == 1:
                    stack_type = "QB+1"
                elif teammate_count == 2:
                    stack_type = "QB+2"
                else:
                    stack_type = "QB+3"
                
                # Check for bring-back
                has_bringback = len(bring_back_players) > 0
                if has_bringback:
                    my_bring_back_count += 1
                
                # Check for secondary game stacks
                has_secondary_game_stack = False
                secondary_stack_details = []
                
                for team, players in team_players.items():
                    if team != qb_team and team != qb_opp and len(players) >= 2:
                        has_secondary_game_stack = True
                        secondary_stack_details.append(f"{team} ({len(players)})")
                        my_secondary_stacks.append(f"{team} Stack ({len(players)} players)")
                
                if has_secondary_game_stack:
                    my_secondary_game_stack_count += 1
                
                my_qb_stack_analysis.append({
                    'Entry': entry['entry_name'],
                    'Rank': entry['rank'],
                    'Points': entry['points'],
                    'Stack_Type': stack_type,
                    'Bring_Back': 'Yes' if has_bringback else 'No',
                    'Secondary_Game_Stack': 'Yes' if has_secondary_game_stack else 'No',
                    'QB': qb_name,
                    'Teammates': teammate_count,
                    'Total_Games': len(game_teams)
                })
            else:
                my_qb_stack_analysis.append({
                    'Entry': entry['entry_name'],
                    'Rank': entry['rank'],
                    'Points': entry['points'],
                    'Stack_Type': 'Unknown',
                    'Bring_Back': 'Unknown',
                    'Secondary_Game_Stack': 'Unknown',
                    'QB': qb_name or 'Unknown',
                    'Teammates': 0,
                    'Total_Games': 0
                })
        
        # Display my stack statistics
        if my_qb_stack_analysis:
            my_qb_stack_df = pd.DataFrame(my_qb_stack_analysis)
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                my_bring_back_pct = (my_bring_back_count / len(my_lineups)) * 100
                winner_bring_back_pct = (bring_back_count / len(winning_lineups)) * 100
                delta = my_bring_back_pct - winner_bring_back_pct
                st.metric("My Bring-Back %", f"{my_bring_back_pct:.1f}%", 
                         delta=f"{delta:+.1f}% vs Winners")
            
            with col2:
                my_secondary_pct = (my_secondary_game_stack_count / len(my_lineups)) * 100
                winner_secondary_pct = (secondary_game_stack_count / len(winning_lineups)) * 100
                delta = my_secondary_pct - winner_secondary_pct
                st.metric("My Secondary Stack %", f"{my_secondary_pct:.1f}%",
                         delta=f"{delta:+.1f}% vs Winners")
            
            with col3:
                my_avg_games = my_qb_stack_df['Total_Games'].mean()
                winner_qb_df = pd.DataFrame(qb_stack_analysis)
                winner_avg_games = winner_qb_df['Total_Games'].mean()
                delta = my_avg_games - winner_avg_games
                st.metric("Avg Games Exposed", f"{my_avg_games:.1f}",
                         delta=f"{delta:+.1f} vs Winners")
            
            with col4:
                my_avg_teammates = my_qb_stack_df['Teammates'].mean()
                winner_avg_teammates = winner_qb_df['Teammates'].mean()
                delta = my_avg_teammates - winner_avg_teammates
                st.metric("Avg QB Stack Size", f"{my_avg_teammates:.1f}",
                         delta=f"{delta:+.1f} vs Winners")
            
            st.markdown("---")
            
            # My stack type distribution vs winners
            st.markdown("#### My Stack Type Distribution vs Winners")
            
            my_stack_dist = my_qb_stack_df['Stack_Type'].value_counts().reset_index()
            my_stack_dist.columns = ['Stack_Type', 'My_Count']
            my_stack_dist['My_Percentage'] = (my_stack_dist['My_Count'] / len(my_qb_stack_analysis)) * 100
            
            winner_stack_dist = winner_qb_df['Stack_Type'].value_counts().reset_index()
            winner_stack_dist.columns = ['Stack_Type', 'Winner_Count']
            winner_stack_dist['Winner_Percentage'] = (winner_stack_dist['Winner_Count'] / len(qb_stack_analysis)) * 100
            
            comparison_df = my_stack_dist.merge(winner_stack_dist, on='Stack_Type', how='outer').fillna(0)
            comparison_df['Difference'] = comparison_df['My_Percentage'] - comparison_df['Winner_Percentage']
            comparison_df = comparison_df.sort_values('Stack_Type')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(
                    comparison_df[['Stack_Type', 'My_Percentage', 'Winner_Percentage', 'Difference']].style.format({
                        'My_Percentage': '{:.1f}%',
                        'Winner_Percentage': '{:.1f}%',
                        'Difference': '{:+.1f}%'
                    }),
                    width='stretch'
                )
            
            with col2:
                fig = px.bar(
                    comparison_df,
                    x='Stack_Type',
                    y=['My_Percentage', 'Winner_Percentage'],
                    title='Stack Type: Me vs Winners',
                    barmode='group',
                    labels={'value': 'Percentage', 'variable': 'Group'}
                )
                st.plotly_chart(fig, width='stretch')
            
            # Detailed entry-by-entry breakdown
            st.markdown("#### My Entries - Detailed Breakdown")
            
            display_cols = ['Entry', 'Rank', 'Points', 'QB', 'Stack_Type', 'Teammates', 'Bring_Back', 'Secondary_Game_Stack', 'Total_Games']
            st.dataframe(
                my_qb_stack_df[display_cols].style.format({
                    'Points': '{:.2f}',
                    'Teammates': '{:.0f}',
                    'Total_Games': '{:.0f}'
                }),
                width='stretch'
            )
        
        st.markdown("---")
        
        # ===== FLEX Position Analysis =====
        st.subheader("🔀 FLEX Position Distribution")
        
        flex_positions = []
        for lineup in winning_lineups:
            for player in lineup:
                if player['position'] == 'FLEX':
                    player_name = player['name']
                    # Get actual position from our map
                    actual_pos = player_pos_map.get(player_name, 'Unknown')
                    flex_positions.append(actual_pos)
        
        if flex_positions:
            flex_df = pd.DataFrame({'Position': flex_positions})
            flex_dist = flex_df['Position'].value_counts().reset_index()
            flex_dist.columns = ['Position', 'Count']
            flex_dist['Percentage'] = (flex_dist['Count'] / len(flex_positions)) * 100
            flex_dist = flex_dist.sort_values('Count', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(
                    flex_dist.style.format({'Percentage': '{:.1f}%'}),
                    width='stretch'
                )
            
            with col2:
                fig = px.bar(
                    flex_dist,
                    x='Position',
                    y='Count',
                    title='FLEX Position Usage',
                    color='Position',
                    text='Count'
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, width='stretch')
        else:
            st.warning("⚠️ Could not determine FLEX positions. Ensure ownership file has position data.")
        
        st.markdown("---")
        st.markdown("### Top Stacks in Winning Lineups")
        
        # Extract QB + pass catchers from winning lineups
        qb_stack_combos = []
        
        for _, row in winners_df.iterrows():
            players = row['players_list']
            
            # Identify QB and receivers/TEs from same team
            # This is simplified - would need team data for precise stacking
            for i in range(len(players)):
                for j in range(i+1, len(players)):
                    qb_stack_combos.append((players[i], players[j]))
        
        stack_counts = Counter(qb_stack_combos)
        
        st.subheader("Most Common 2-Player Combinations in Top 0.1%")
        
        top_stacks = pd.DataFrame([
            {'Player 1': combo[0], 'Player 2': combo[1], 'Appearances': count}
            for combo, count in stack_counts.most_common(20)
        ])
        
        st.dataframe(top_stacks, width='stretch')
        
        # Most popular individual players in winning lineups
        st.subheader("Most Rostered Players in Top 0.1%")
        
        winner_roster_df = pd.DataFrame([
            {'Player': player, 'Appearances': count, 'Win_Rate%': (count/total_winners)*100}
            for player, count in winner_player_counts.most_common(20)
        ])
        
        # Merge with ownership to show leverage
        if 'name' in ownership_df.columns:
            winner_roster_df = winner_roster_df.merge(
                ownership_df[['name', 'Own%', 'FPTS']],
                left_on='Player',
                right_on='name',
                how='left'
            )
            
            winner_roster_df['Leverage'] = winner_roster_df['Win_Rate%'] - winner_roster_df['Own%']
        
        st.dataframe(
            winner_roster_df.style.format({
                'Win_Rate%': '{:.1f}%',
                'Own%': '{:.1f}%',
                'Leverage': '{:.1f}%',
                'FPTS': '{:.1f}'
            }),
            width='stretch'
        )
    
    # --------------------------------------------------------
    # TAB 4: My Performance Analysis
    # --------------------------------------------------------
    with tab4:
        st.header("📈 My Performance Analysis")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_score = my_entries_df['Points'].mean()
            st.metric("Avg Score", f"{avg_score:.1f}")
        
        with col2:
            best_score = my_entries_df['Points'].max()
            best_rank = my_entries_df['Rank'].min()
            st.metric("Best Finish", f"#{best_rank}", f"{best_score:.1f} pts")
        
        with col3:
            top_winner_score = winners_df['Points'].iloc[0]
            gap = top_winner_score - best_score
            st.metric("Gap to Winner", f"{gap:.1f} pts")
        
        with col4:
            total_entries = 4705  # From your data
            percentile = (1 - best_rank/total_entries) * 100
            st.metric("Top Percentile", f"{percentile:.1f}%")
        
        st.markdown("---")
        
        # Lineup breakdown
        st.subheader("My Lineup Results")
        
        display_df = my_entries_df[['Rank', 'EntryName', 'Points']].copy()
        display_df = display_df.sort_values('Rank')
        
        st.dataframe(
            display_df.style.format({'Points': '{:.2f}'}),
            width='stretch'
        )
        
        # Player overlap with winners
        st.subheader("My Players vs Winners")
        
        overlap_analysis = []
        for player, my_count in my_player_counts.most_common():
            winner_count = winner_player_counts.get(player, 0)
            winner_pct = (winner_count / total_winners) * 100
            
            # Get ownership and FPTS
            player_data = ownership_df[ownership_df['name'] == player]
            if not player_data.empty:
                own_pct = player_data['Own%'].iloc[0]
                fpts = player_data['FPTS'].iloc[0]
            else:
                own_pct = 0
                fpts = 0
            
            overlap_analysis.append({
                'Player': player,
                'My_Lineups': my_count,
                'Winner_Lineups': winner_count,
                'Winner%': winner_pct,
                'Field_Own%': own_pct,
                'FPTS': fpts
            })
        
        overlap_df = pd.DataFrame(overlap_analysis)
        overlap_df = overlap_df.sort_values('My_Lineups', ascending=False)
        
        st.dataframe(
            overlap_df.style.format({
                'Winner%': '{:.1f}%',
                'Field_Own%': '{:.1f}%',
                'FPTS': '{:.1f}'
            }),
            width='stretch'
        )
    
    # --------------------------------------------------------
    # TAB 5: Boom/Bust Accuracy
    # --------------------------------------------------------
    with tab5:
        st.header("🔬 Boom/Bust Projection Accuracy")
        
        st.markdown("""
        Comparing pre-contest boom projections vs actual results
        """)
        
        # Merge boom/bust projections with actual results
        if 'name' in boom_bust_df.columns and 'Boom%' in boom_bust_df.columns:
            accuracy_df = boom_bust_df.merge(
                ownership_df[['name', 'FPTS']],
                on='name',
                how='inner'
            )
            
            # Calculate if player boomed (need boom threshold logic)
            # Using simple heuristic: FPTS > ceiling_adj = boom
            if 'ceiling_adj' in accuracy_df.columns:
                accuracy_df['Actually_Boomed'] = accuracy_df['FPTS'] > accuracy_df['ceiling_adj']
                accuracy_df['Boom_Prob'] = accuracy_df['Boom%'] / 100
                
                # Sort by boom probability
                accuracy_df = accuracy_df.sort_values('Boom%', ascending=False)
                
                st.subheader("Top Projected Boom Plays - Results")
                
                top_boom_projected = accuracy_df.head(20)[[
                    'name', 'position', 'Salary', 'Own%', 'Boom%', 
                    'proj_adj', 'ceiling_adj', 'FPTS', 'Actually_Boomed'
                ]]
                
                st.dataframe(
                    top_boom_projected.style
                    .format({
                        'Salary': '${:,.0f}',
                        'Own%': '{:.1f}%',
                        'Boom%': '{:.1f}%',
                        'proj_adj': '{:.1f}',
                        'ceiling_adj': '{:.1f}',
                        'FPTS': '{:.1f}'
                    })
                    .map(
                        lambda v: 'background-color: #2ECC71' if v == True else 
                                  'background-color: #E74C3C' if v == False else '',
                        subset=['Actually_Boomed']
                    ),
                    width='stretch'
                )
                
                # Accuracy metrics
                st.subheader("Model Performance Metrics")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # High boom% players (>25%) - how many hit?
                    high_boom = accuracy_df[accuracy_df['Boom%'] > 25]
                    hit_rate = high_boom['Actually_Boomed'].sum() / len(high_boom) * 100
                    st.metric("High Boom% Hit Rate", f"{hit_rate:.1f}%", 
                             help="Players with >25% boom probability")
                
                with col2:
                    # Correlation between boom% and actual performance
                    corr = accuracy_df[['Boom%', 'FPTS']].corr().iloc[0, 1]
                    st.metric("Boom% ↔ FPTS Correlation", f"{corr:.3f}")
                
                with col3:
                    # Top leverage misses (high boom%, low owned, didn't hit)
                    misses = accuracy_df[
                        (accuracy_df['Boom%'] > 20) & 
                        (accuracy_df['Own%'] < 15) &
                        (accuracy_df['Actually_Boomed'] == False)
                    ]
                    st.metric("Good Leverage Whiffs", len(misses),
                             help="High boom%, low owned plays that didn't hit")
                
                # Projection accuracy scatter
                st.subheader("Projected vs Actual Performance")
                
                fig = px.scatter(
                    accuracy_df,
                    x='proj_adj',
                    y='FPTS',
                    color='Boom%',
                    size='Own%',
                    hover_data=['name', 'position', 'Salary', 'ceiling_adj'],
                    color_continuous_scale='RdBu_r',
                    title='Projection Accuracy (size = ownership, color = boom%)',
                    labels={
                        'proj_adj': 'Projected Points (proj_adj)',
                        'FPTS': 'Actual Points (FPTS)',
                        'Boom%': 'Boom %'
                    }
                )
                
                # Add diagonal line (perfect projection)
                max_val = max(accuracy_df['proj_adj'].max(), accuracy_df['FPTS'].max())
                fig.add_trace(go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode='lines',
                    line=dict(color='black', dash='dash', width=2),
                    name='Perfect Projection',
                    showlegend=True
                ))
                
                fig.update_traces(marker=dict(opacity=0.7))
                fig.update_layout(height=600, hovermode='closest')
                
                st.plotly_chart(fig, width='stretch')

    # --------------------------------------------------------
    # TAB 6: ROI Tracker
    # --------------------------------------------------------
    with tab6:
        st.header("💰 ROI Tracker")
        
        st.markdown("""
        Calculate your return on investment based on contest payout structure
        """)
        
        # Payout structure
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
        
        # Calculate winnings for my entries
        my_entries_df['Payout'] = my_entries_df['Rank'].apply(get_payout)
        total_winnings = my_entries_df['Payout'].sum()
        
        # Entry fee input
        col1, col2 = st.columns(2)
        
        with col1:
            entry_fee = st.number_input(
                "Entry Fee per Lineup ($)",
                min_value=0.0,
                value=10.0,
                step=1.0,
                help="What did you pay per entry?"
            )
        
        with col2:
            num_entries = len(my_entries_df)
            total_invested = entry_fee * num_entries
            st.metric("Total Entries", num_entries)
        
        # ROI Calculations
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💵 Total Invested", f"${total_invested:.2f}")
        
        with col2:
            st.metric("💰 Total Winnings", f"${total_winnings:.2f}")
        
        with col3:
            net_profit = total_winnings - total_invested
            st.metric("📊 Net Profit/Loss", f"${net_profit:.2f}", 
                     delta=f"{net_profit:.2f}")
        
        with col4:
            roi_pct = ((total_winnings - total_invested) / total_invested * 100) if total_invested > 0 else 0
            st.metric("📈 ROI", f"{roi_pct:.1f}%",
                     delta=f"{roi_pct:.1f}%" if roi_pct >= 0 else None)
        
        st.markdown("---")
        
        # Detailed breakdown
        st.subheader("💵 Entry-by-Entry Breakdown")
        
        breakdown_df = my_entries_df[['Rank', 'EntryName', 'Points', 'Payout']].copy()
        breakdown_df['Entry Fee'] = entry_fee
        breakdown_df['Net'] = breakdown_df['Payout'] - breakdown_df['Entry Fee']
        breakdown_df = breakdown_df.sort_values('Rank')
        
        # Color code by profitability
        def color_net(val):
            if val > 0:
                return 'background-color: #2ECC71; color: white;'
            elif val < 0:
                return 'background-color: #E74C3C; color: white;'
            else:
                return 'background-color: #F39C12; color: white;'
        
        st.dataframe(
            breakdown_df.style
            .format({
                'Points': '{:.2f}',
                'Payout': '${:.2f}',
                'Entry Fee': '${:.2f}',
                'Net': '${:.2f}'
            })
            .map(color_net, subset=['Net']),
            width='stretch'
        )
        
        # Payout structure reference
        st.markdown("---")
        st.subheader("📋 Full Payout Structure")
        
        payout_ref = []
        for key, value in payout_structure.items():
            if isinstance(key, tuple):
                payout_ref.append({
                    'Rank': f"{key[0]} - {key[1]}",
                    'Payout': f"${value:.2f}"
                })
            else:
                payout_ref.append({
                    'Rank': f"{key}",
                    'Payout': f"${value:.2f}"
                })
        
        payout_ref_df = pd.DataFrame(payout_ref)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(
                payout_ref_df.head(10),
                hide_index=True,
                width='stretch'
            )
        
        with col2:
            st.dataframe(
                payout_ref_df.tail(10),
                hide_index=True,
                width='stretch'
            )
        
        # ROI Analysis
        st.markdown("---")
        st.subheader("📊 ROI Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Cash rate
            cashing_entries = len(breakdown_df[breakdown_df['Payout'] > 0])
            cash_rate = (cashing_entries / num_entries * 100) if num_entries > 0 else 0
            
            st.metric("💵 Cash Rate", f"{cash_rate:.1f}%",
                     help=f"{cashing_entries} out of {num_entries} entries cashed")
            
            # Best finish analysis
            best_rank = breakdown_df['Rank'].min()
            best_payout = breakdown_df['Payout'].max()
            st.metric("🏆 Best Finish", f"#{best_rank}", f"${best_payout:.2f}")
        
        with col2:
            # Average finish
            avg_rank = breakdown_df['Rank'].mean()
            st.metric("📊 Average Rank", f"#{avg_rank:.0f}")
            
            # Break-even analysis
            break_even_rank = None
            for rank in range(1, 1047):
                if get_payout(rank) >= entry_fee:
                    break_even_rank = rank
            
            if break_even_rank:
                st.metric("⚖️ Break-Even Rank", f"#{break_even_rank}",
                         help=f"Need to finish #{break_even_rank} or better to profit per entry")

    # --------------------------------------------------------
    # TAB 7: Post-Contest Simulator
    # --------------------------------------------------------
    with tab7:
        st.header("🎲 Post-Contest Simulator")
        
        st.markdown("""
        **Remove variance from your results.** This simulator runs thousands of iterations using your projection distributions
        to calculate how your lineups would perform across all possible outcomes. This reveals true lineup quality beyond
        the single actual outcome.
        """)
        
        # ===== SIMULATION ENGINE =====
        st.subheader("⚙️ Simulation Settings")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            n_simulations = st.number_input("Number of Simulations", min_value=100, max_value=10000, value=1000, step=100,
                                           help="More simulations = more accurate but slower")
        with col2:
            contest_size = st.number_input("Full Contest Size", min_value=100, value=4705, step=1,
                                          help="Total number of entries in the contest")
        with col3:
            entry_fee = st.number_input("Entry Fee ($)", min_value=0.0, value=10.0, step=1.0)
            run_sim = st.button("🚀 Run Simulation", type="primary")
        
        if run_sim:
            with st.spinner(f"Running {n_simulations:,} simulations..."):
                
                # Prepare player simulation data
                sim_players = boom_bust_df.copy()
                
                # Ensure we have necessary columns
                required_cols = ['name', 'proj_adj', 'ceiling_adj']
                missing_cols = [col for col in required_cols if col not in sim_players.columns]
                
                if missing_cols:
                    st.error(f"❌ Missing required columns in boom/bust file: {missing_cols}")
                    st.stop()
                
                # Calculate standard deviation if not present
                if 'stddev_adj' not in sim_players.columns:
                    # Estimate stddev from projection to ceiling range
                    # Assume ceiling is ~2 standard deviations above projection
                    sim_players['stddev_adj'] = (sim_players['ceiling_adj'] - sim_players['proj_adj']) / 2.0
                
                # Create player name to stats mapping
                player_stats = {}
                for _, row in sim_players.iterrows():
                    player_name = row['name']
                    player_stats[player_name] = {
                        'mean': row['proj_adj'],
                        'std': row.get('stddev_adj', (row['ceiling_adj'] - row['proj_adj']) / 2.0),
                        'floor': max(0, row['proj_adj'] - 2 * row.get('stddev_adj', (row['ceiling_adj'] - row['proj_adj']) / 2.0)),
                        'ceiling': row['ceiling_adj']
                    }
                
                # Parse all contest lineups
                all_lineups = []
                
                # Add my lineups
                for idx, row in my_entries_df.iterrows():
                    lineup_players = parse_lineup(row[lineup_col])
                    all_lineups.append({
                        'entry_id': row.get('EntryId', f'my_{idx}'),
                        'entry_name': row.get('EntryName', f'My Entry {idx}'),
                        'rank': row.get('Rank', None),
                        'actual_points': row.get('Points', None),
                        'players': lineup_players,
                        'is_mine': True
                    })
                
                # Add field lineups (sample for performance if too many)
                field_sample_size = min(1000, len(winners_df))
                field_sample = winners_df.sample(n=field_sample_size) if len(winners_df) > field_sample_size else winners_df
                
                for idx, row in field_sample.iterrows():
                    lineup_players = parse_lineup(row[lineup_col])
                    all_lineups.append({
                        'entry_id': row.get('EntryId', f'field_{idx}'),
                        'entry_name': row.get('EntryName', f'Field Entry {idx}'),
                        'rank': row.get('Rank', None),
                        'actual_points': row.get('Points', None),
                        'players': lineup_players,
                        'is_mine': False
                    })
                
                st.info(f"📊 Simulating {len(all_lineups)} lineups ({len(my_entries_df)} yours, {len(field_sample)} field)")
                
                # Run simulations
                progress_bar = st.progress(0)
                lineup_sim_scores = {i: [] for i in range(len(all_lineups))}
                
                np.random.seed(42)  # For reproducibility
                
                for sim_num in range(n_simulations):
                    # Generate simulated scores for all players
                    sim_player_scores = {}
                    
                    for player_name, stats in player_stats.items():
                        # Use truncated normal distribution
                        score = np.random.normal(stats['mean'], stats['std'])
                        # Clamp to floor/ceiling
                        score = max(stats['floor'], min(stats['ceiling'], score))
                        sim_player_scores[player_name] = score
                    
                    # Score each lineup
                    for lineup_idx, lineup_data in enumerate(all_lineups):
                        lineup_score = 0
                        for player_name in lineup_data['players']:
                            if player_name in sim_player_scores:
                                lineup_score += sim_player_scores[player_name]
                        
                        lineup_sim_scores[lineup_idx].append(lineup_score)
                    
                    # Update progress
                    if sim_num % 100 == 0:
                        progress_bar.progress((sim_num + 1) / n_simulations)
                
                progress_bar.progress(1.0)
                st.success(f"✅ Completed {n_simulations:,} simulations!")
                
                # ===== ANALYZE SIMULATION RESULTS =====
                st.markdown("---")
                st.subheader("📈 Simulation Results")
                
                # Use the user-specified contest size
                st.info(f"📊 Analyzing {len(all_lineups)} lineups. Ranks will be scaled to represent {contest_size:,} total entries.")
                
                # Calculate metrics for each lineup
                lineup_results = []
                
                for lineup_idx, lineup_data in enumerate(all_lineups):
                    sim_scores = lineup_sim_scores[lineup_idx]
                    
                    # Calculate average finish across simulations
                    avg_finishes = []
                    total_winnings = 0
                    
                    for sim_num in range(n_simulations):
                        # Get all scores for this simulation
                        all_sim_scores = [lineup_sim_scores[i][sim_num] for i in range(len(all_lineups))]
                        
                        # Rank this lineup within the sample
                        lineup_score = sim_scores[sim_num]
                        sample_rank = sum(1 for score in all_sim_scores if score > lineup_score) + 1
                        
                        # Calculate percentile within sample
                        percentile = sample_rank / len(all_lineups)
                        
                        # Scale to full contest size
                        estimated_rank = int(percentile * contest_size)
                        estimated_rank = max(1, min(contest_size, estimated_rank))
                        
                        avg_finishes.append(estimated_rank)
                        
                        # Calculate winnings based on scaled rank
                        payout = get_payout(estimated_rank)
                        total_winnings += payout
                    
                    avg_finish = np.mean(avg_finishes)
                    avg_winnings = total_winnings / n_simulations
                    sim_roi = ((avg_winnings - entry_fee) / entry_fee) * 100 if entry_fee > 0 else 0
                    
                    lineup_results.append({
                        'Entry_ID': lineup_data['entry_id'],
                        'Entry_Name': lineup_data['entry_name'],
                        'Is_Mine': lineup_data['is_mine'],
                        'Actual_Rank': lineup_data['rank'],
                        'Actual_Points': lineup_data['actual_points'],
                        'Sim_Avg_Points': np.mean(sim_scores),
                        'Sim_Std_Points': np.std(sim_scores),
                        'Sim_Avg_Finish': avg_finish,
                        'Sim_Avg_Winnings': avg_winnings,
                        'Sim_ROI': sim_roi,
                        'Players': lineup_data['players']
                    })
                
                results_df = pd.DataFrame(lineup_results)
                
                # ===== MY PORTFOLIO ANALYSIS =====
                st.subheader("📋 My Portfolio Analysis")
                
                my_results = results_df[results_df['Is_Mine'] == True].copy()
                field_results = results_df[results_df['Is_Mine'] == False].copy()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    my_avg_roi = my_results['Sim_ROI'].mean()
                    field_avg_roi = field_results['Sim_ROI'].mean()
                    delta = my_avg_roi - field_avg_roi
                    st.metric("My Avg Sim ROI", f"{my_avg_roi:.1f}%", 
                             delta=f"{delta:+.1f}% vs Field")
                
                with col2:
                    my_avg_proj = my_results['Sim_Avg_Points'].mean()
                    field_avg_proj = field_results['Sim_Avg_Points'].mean()
                    delta = my_avg_proj - field_avg_proj
                    st.metric("My Avg Proj Points", f"{my_avg_proj:.1f}",
                             delta=f"{delta:+.1f} vs Field")
                
                with col3:
                    my_avg_finish = my_results['Sim_Avg_Finish'].mean()
                    field_avg_finish = field_results['Sim_Avg_Finish'].mean()
                    delta = field_avg_finish - my_avg_finish  # Reverse: lower is better
                    st.metric("My Avg Finish", f"{my_avg_finish:.1f}",
                             delta=f"{delta:+.1f} vs Field" if delta > 0 else f"{delta:.1f} vs Field")
                
                with col4:
                    total_invested = len(my_results) * entry_fee
                    total_exp_winnings = my_results['Sim_Avg_Winnings'].sum()
                    portfolio_roi = ((total_exp_winnings - total_invested) / total_invested) * 100 if total_invested > 0 else 0
                    st.metric("Portfolio Sim ROI", f"{portfolio_roi:.1f}%")
                
                st.markdown("---")
                
                # ===== LINEUP BREAKDOWN =====
                st.subheader("🔍 My Lineup Breakdown")
                
                # Sort my lineups by Sim ROI
                my_results_sorted = my_results.sort_values('Sim_ROI', ascending=False)
                
                display_cols = ['Entry_Name', 'Actual_Rank', 'Actual_Points', 'Sim_Avg_Points', 
                               'Sim_Avg_Finish', 'Sim_Avg_Winnings', 'Sim_ROI']
                
                st.dataframe(
                    my_results_sorted[display_cols].style.format({
                        'Actual_Points': '{:.2f}',
                        'Sim_Avg_Points': '{:.2f}',
                        'Sim_Avg_Finish': '{:.1f}',
                        'Sim_Avg_Winnings': '${:.2f}',
                        'Sim_ROI': '{:.1f}%'
                    }),
                    width='stretch',
                    height=400
                )
                
                # Best and Worst Lineups
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🏆 Best Sim ROI Lineups")
                    best_lineups = my_results_sorted.head(3)
                    for idx, row in best_lineups.iterrows():
                        with st.expander(f"{row['Entry_Name']} - ROI: {row['Sim_ROI']:.1f}%"):
                            st.write(f"**Sim Avg Points:** {row['Sim_Avg_Points']:.2f}")
                            st.write(f"**Sim Avg Finish:** {row['Sim_Avg_Finish']:.1f}")
                            st.write(f"**Players:** {', '.join(row['Players'])}")
                
                with col2:
                    st.markdown("#### 📉 Worst Sim ROI Lineups")
                    worst_lineups = my_results_sorted.tail(3)
                    for idx, row in worst_lineups.iterrows():
                        with st.expander(f"{row['Entry_Name']} - ROI: {row['Sim_ROI']:.1f}%"):
                            st.write(f"**Sim Avg Points:** {row['Sim_Avg_Points']:.2f}")
                            st.write(f"**Sim Avg Finish:** {row['Sim_Avg_Finish']:.1f}")
                            st.write(f"**Players:** {', '.join(row['Players'])}")
                
                st.markdown("---")
                
                # ===== PLAYER ROI ANALYSIS =====
                st.subheader("🎯 Player Sim ROI Analysis")
                
                st.markdown("""
                **Sim Player ROI** = Average ROI of all lineups containing that player.
                High ROI players were objectively good plays regardless of actual outcome.
                """)
                
                # Calculate player ROI
                player_roi_data = {}
                
                for _, lineup in my_results.iterrows():
                    for player in lineup['Players']:
                        if player not in player_roi_data:
                            player_roi_data[player] = {
                                'lineups': 0,
                                'total_roi': 0,
                                'total_proj': 0
                            }
                        
                        player_roi_data[player]['lineups'] += 1
                        player_roi_data[player]['total_roi'] += lineup['Sim_ROI']
                        player_roi_data[player]['total_proj'] += lineup['Sim_Avg_Points']
                
                # Create player ROI dataframe
                player_roi_list = []
                for player, data in player_roi_data.items():
                    avg_roi = data['total_roi'] / data['lineups']
                    
                    # Get player info from ownership
                    player_info = ownership_df[ownership_df['name'] == player]
                    
                    if not player_info.empty:
                        field_own = player_info.iloc[0].get('Own%', 0)
                        actual_pts = player_info.iloc[0].get('FPTS', 0)
                        position = player_info.iloc[0].get('position', 'N/A')
                        salary = player_info.iloc[0].get('Salary', 0)
                    else:
                        field_own = 0
                        actual_pts = 0
                        position = 'N/A'
                        salary = 0
                    
                    my_own = (data['lineups'] / len(my_results)) * 100
                    
                    player_roi_list.append({
                        'Player': player,
                        'Position': position,
                        'Salary': salary,
                        'Sim_Player_ROI': avg_roi,
                        'My_Own%': my_own,
                        'Field_Own%': field_own,
                        'Own_Diff': my_own - field_own,
                        'Actual_FPTS': actual_pts,
                        'Lineups': data['lineups']
                    })
                
                player_roi_df = pd.DataFrame(player_roi_list)
                player_roi_df = player_roi_df.sort_values('Sim_Player_ROI', ascending=False)
                
                # Display top and bottom players
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### ⭐ Highest Sim Player ROI")
                    top_players = player_roi_df.head(15)
                    
                    display_cols = ['Player', 'Position', 'Sim_Player_ROI', 'My_Own%', 'Field_Own%', 'Own_Diff']
                    st.dataframe(
                        top_players[display_cols].style.format({
                            'Sim_Player_ROI': '{:.1f}%',
                            'My_Own%': '{:.1f}%',
                            'Field_Own%': '{:.1f}%',
                            'Own_Diff': '{:+.1f}%'
                        }).background_gradient(subset=['Sim_Player_ROI'], cmap='Greens'),
                        width='stretch'
                    )
                
                with col2:
                    st.markdown("#### 💔 Lowest Sim Player ROI")
                    bottom_players = player_roi_df.tail(15)
                    
                    st.dataframe(
                        bottom_players[display_cols].style.format({
                            'Sim_Player_ROI': '{:.1f}%',
                            'My_Own%': '{:.1f}%',
                            'Field_Own%': '{:.1f}%',
                            'Own_Diff': '{:+.1f}%'
                        }).background_gradient(subset=['Sim_Player_ROI'], cmap='Reds_r'),
                        width='stretch'
                    )
                
                # Ownership analysis
                st.markdown("---")
                st.markdown("#### 📊 Ownership vs Sim Player ROI")
                
                fig = px.scatter(
                    player_roi_df,
                    x='Field_Own%',
                    y='Sim_Player_ROI',
                    size='Actual_FPTS',
                    color='Own_Diff',
                    hover_data=['Player', 'Position', 'Salary', 'My_Own%'],
                    color_continuous_scale='RdYlGn',
                    title='Field Ownership vs Player Sim ROI (size = actual points, color = your ownership difference)',
                    labels={
                        'Field_Own%': 'Field Ownership %',
                        'Sim_Player_ROI': 'Sim Player ROI %',
                        'Own_Diff': 'Your Own Diff'
                    }
                )
                
                fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break-even ROI")
                fig.update_layout(height=600)
                
                st.plotly_chart(fig, width='stretch')
                
                # Key insights
                st.markdown("---")
                st.subheader("💡 Key Insights")
                
                # High ROI players you missed
                high_roi_missed = player_roi_df[
                    (player_roi_df['Sim_Player_ROI'] > 20) & 
                    (player_roi_df['Own_Diff'] < -10)
                ].head(5)
                
                if not high_roi_missed.empty:
                    st.markdown("**🔍 High ROI Plays You Underweighted:**")
                    for _, row in high_roi_missed.iterrows():
                        st.write(f"- **{row['Player']}** ({row['Position']}): {row['Sim_Player_ROI']:.1f}% ROI, "
                                f"Field {row['Field_Own%']:.1f}%, You {row['My_Own%']:.1f}% "
                                f"({row['Own_Diff']:+.1f}%)")
                
                # Low ROI players you overplayed
                low_roi_overplayed = player_roi_df[
                    (player_roi_df['Sim_Player_ROI'] < -20) & 
                    (player_roi_df['Own_Diff'] > 10)
                ].head(5)
                
                if not low_roi_overplayed.empty:
                    st.markdown("**⚠️ Low ROI Plays You Overweighted:**")
                    for _, row in low_roi_overplayed.iterrows():
                        st.write(f"- **{row['Player']}** ({row['Position']}): {row['Sim_Player_ROI']:.1f}% ROI, "
                                f"Field {row['Field_Own%']:.1f}%, You {row['My_Own%']:.1f}% "
                                f"({row['Own_Diff']:+.1f}%)")
        
        else:
            st.info("👆 Click 'Run Simulation' to analyze your lineup quality across thousands of scenarios")

else:
    st.info("👈 Please upload all 4 CSV files in the sidebar to begin analysis")
    
    st.markdown("""
    ### Expected File Formats:
    
    **1. Player Ownership & FPTS:**
    - Columns: `name`, `Own%`, `FPTS`, `position`, `Salary`
    
    **2. Contest Top 0.1%:**
    - Columns: `Rank`, `EntryId`, `EntryName`, `Points`, `Lineup`
    
    **3. My Entries:**
    - Columns: `Rank`, `EntryId`, `EntryName`, `Points`, `Lineup`
    
    **4. Player Boom/Bust Projections:**
    - Columns: `name`, `Boom%`, `proj_adj`, `ceiling_adj`, `stddev_adj`, `Own%`, etc.
    """)
