import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import itertools

st.title("🏆 DFS Contest Analyzer")

st.info("📊 **Post-Contest Analysis Tool** - Upload DraftKings contest results CSV to analyze performance, leverage, stacks, and identify areas for improvement.")

# --------------------------------------------------------
# File Upload Section
# --------------------------------------------------------
st.sidebar.header("📁 Upload Contest Data")

contest_file = st.sidebar.file_uploader(
    "DraftKings Contest Results CSV", 
    type=['csv'],
    help="Download contest results from DraftKings (includes all entries, lineups, ownership, and FPTS)"
)

roo_file = st.sidebar.file_uploader(
    "ROO Projections CSV",
    type=['csv'],
    help="Upload your ROO projections file to map player teams for stack analysis"
)

# --------------------------------------------------------
# Load and Process Data
# --------------------------------------------------------
if contest_file:
    
    # Load data - DraftKings CSV has two data structures side-by-side
    # Columns A-F: Contest entries (Rank, EntryId, EntryName, TimeRemaining, Points, Lineup)
    # Column G: Empty separator
    # Columns H-K: Player pool (Player, Roster Position, %Drafted, FPTS)
    
    raw_df = pd.read_csv(contest_file)
    
    # Split into two dataframes
    # Contest entries (first 6 columns)
    contest_cols = ['Rank', 'EntryId', 'EntryName', 'TimeRemaining', 'Points', 'Lineup']
    df = raw_df[contest_cols].copy()
    
    # Player pool data (columns after the separator)
    player_cols = ['Player', 'Roster Position', '%Drafted', 'FPTS']
    player_pool = raw_df[player_cols].copy()
    
    # Remove duplicate player rows (they repeat for each contest entry)
    player_stats = player_pool.dropna(subset=['Player']).drop_duplicates(subset=['Player']).copy()
    
    # Trim whitespace from player names (DraftKings has trailing spaces on DST names)
    player_stats['Player'] = player_stats['Player'].str.strip()
    
    # Clean ownership percentages
    player_stats['Own%'] = player_stats['%Drafted'].str.rstrip('%').astype(float)
    player_stats = player_stats.rename(columns={'Roster Position': 'Position'})
    
    # Create DST name mapping (lineup has "Seahawks", player pool has "Seahawks D/ST")
    dst_name_map = {}
    for idx, row in player_stats[player_stats['Position'] == 'DST'].iterrows():
        full_name = row['Player']
        # Extract team name before " D/ST" or " DST"
        if ' D/ST' in full_name:
            short_name = full_name.replace(' D/ST', '')
        elif ' DST' in full_name:
            short_name = full_name.replace(' DST', '')
        else:
            short_name = full_name
        dst_name_map[short_name] = full_name
    
    # Load ROO projections for team mapping
    player_team_map = {}
    player_position_map = {}  # For FLEX resolution
    if roo_file:
        roo_df = pd.read_csv(roo_file)
        # ROO uses 'Player' column (not 'Name')
        if 'Player' in roo_df.columns and 'Team' in roo_df.columns:
            player_team_map = dict(zip(roo_df['Player'], roo_df['Team']))
            if 'Position' in roo_df.columns:
                player_position_map = dict(zip(roo_df['Player'], roo_df['Position']))
            st.success(f"✅ Loaded {len(df)} contest entries, {len(player_stats)} unique players, and {len(player_team_map)} player-team mappings!")
        else:
            st.warning("⚠️ ROO file missing 'Player' or 'Team' columns. Team analysis may be limited.")
            st.success(f"✅ Loaded {len(df)} contest entries and {len(player_stats)} unique players!")
    else:
        st.success(f"✅ Loaded {len(df)} contest entries and {len(player_stats)} unique players!")
        st.info("💡 Upload ROO Projections CSV for enhanced team-based stack analysis")
    
    # Fallback: create position map from player_stats for FLEX resolution
    player_stats_position_map = dict(zip(player_stats['Player'], player_stats['Position']))
    
    # --------------------------------------------------------
    # Data Processing
    # --------------------------------------------------------
    
    # Show raw data structure for debugging
    with st.expander("🔍 Debug: Raw Data", expanded=False):
        st.write("**Contest Entry Columns:**", contest_cols)
        st.write("**Player Pool Columns:**", player_cols)
        st.write("**Sample Contest Entries:**")
        st.dataframe(df.head(3))
        st.write("**Sample Player Stats:**")
        st.dataframe(player_stats.head(5))
    
    # Parse usernames from EntryName (remove entry count suffix like "(4/20)")
    def parse_username(entry_name):
        """Extract username from 'Username (4/20)' format"""
        if pd.isna(entry_name):
            return None
        # Split on first '(' and take everything before it, strip whitespace
        username = str(entry_name).split('(')[0].strip()
        return username if username else None
    
    df['Username'] = df['EntryName'].apply(parse_username)
    
    # Extract unique usernames for dropdown
    usernames = df['Username'].dropna().unique()
    usernames = sorted(usernames)
    
    # User selection dropdown
    st.sidebar.markdown("---")
    st.sidebar.header("👤 Select User")
    
    selected_user = st.sidebar.selectbox(
        "Choose username:",
        options=["All Users"] + list(usernames),
        help="Select a user to analyze their entries vs the field"
    )
    
    # Parse lineups from the Lineup column (before filtering)
    def parse_dk_lineup_detailed(lineup_str):
        """
        Parse DraftKings lineup format with positions.
        Returns: list of dicts with 'player', 'position', and 'team' keys
        """
        if pd.isna(lineup_str):
            return []
        
        lineup_str = str(lineup_str).strip()
        lineup_players = []
        
        # Split by position prefixes and extract player names with positions
        positions = ['DST', 'FLEX', 'QB', 'RB', 'TE', 'WR']
        tokens = lineup_str.split()
        
        i = 0
        while i < len(tokens):
            if tokens[i] in positions:
                position = tokens[i]
                # Next tokens until we hit another position are the player name
                i += 1
                player_parts = []
                while i < len(tokens) and tokens[i] not in positions:
                    player_parts.append(tokens[i])
                    i += 1
                if player_parts:
                    player_name = ' '.join(player_parts)
                    lineup_players.append({
                        'player': player_name,
                        'position': position
                    })
            else:
                i += 1
        
        return lineup_players
    
    def parse_dk_lineup(lineup_str):
        """Extract just player names for backwards compatibility"""
        detailed = parse_dk_lineup_detailed(lineup_str)
        return [p['player'] for p in detailed]
    
    # Parse lineups with detailed info
    df['lineup_detailed'] = df['Lineup'].apply(parse_dk_lineup_detailed)
    
    # Add team information and resolve FLEX positions using ROO projections
    def add_team_and_position_to_lineup(lineup_detailed, team_map, pos_map, stats_pos_map, dst_map):
        """Add team info and resolve FLEX to actual position"""
        for player_dict in lineup_detailed:
            player_name = player_dict['player']
            
            # Handle DST name mapping ("Seahawks" -> "Seahawks D/ST")
            if player_dict['position'] == 'DST' and player_name in dst_map:
                mapped_name = dst_map[player_name]
                player_dict['player'] = mapped_name
                player_name = mapped_name
            
            # Look up team in ROO projections
            player_dict['team'] = team_map.get(player_name, 'UNK')
            
            # Resolve FLEX position to actual position (RB/WR/TE)
            if player_dict['position'] == 'FLEX':
                # Try ROO position map first
                if player_name in pos_map:
                    player_dict['actual_position'] = pos_map[player_name]
                    player_dict['is_flex'] = True
                # Fallback to player_stats position map
                elif player_name in stats_pos_map:
                    player_dict['actual_position'] = stats_pos_map[player_name]
                    player_dict['is_flex'] = True
                else:
                    player_dict['actual_position'] = 'FLEX'
                    player_dict['is_flex'] = True
            else:
                player_dict['actual_position'] = player_dict['position']
                player_dict['is_flex'] = False
        return lineup_detailed
    
    df['lineup_detailed'] = df['lineup_detailed'].apply(
        lambda x: add_team_and_position_to_lineup(x, player_team_map, player_position_map, player_stats_position_map, dst_name_map)
    )
    
    # Extract player names from lineup_detailed (after DST mapping)
    df['players'] = df['lineup_detailed'].apply(lambda x: [p['player'] for p in x])
    
    # Debug: Show sample parsed lineups
    with st.expander("🔍 Debug: Lineup Parsing", expanded=False):
        sample_entry = df.iloc[0]
        st.write("**Sample Lineup String:**")
        st.code(sample_entry['Lineup'])
        st.write("**Parsed Players (Simple):**")
        st.write(sample_entry['players'])
        st.write(f"**Number of players parsed:** {len(sample_entry['players'])}")
        
        st.write("**Parsed Lineup (Detailed with Positions & Teams):**")
        st.json(sample_entry['lineup_detailed'])
        
        # Show FLEX distribution
        st.write("**FLEX Position Distribution:**")
        all_flex_players = []
        for lineup_det in df['lineup_detailed']:
            for p in lineup_det:
                if p.get('is_flex', False):
                    all_flex_players.append(p)
        
        if all_flex_players:
            flex_positions = [p['actual_position'] for p in all_flex_players]
            flex_counter = Counter(flex_positions)
            flex_total = len(flex_positions)
            
            flex_dist_df = pd.DataFrame([
                {'Position': pos, 'Count': count, 'Percentage': f"{(count/flex_total)*100:.1f}%"}
                for pos, count in flex_counter.most_common()
            ])
            st.dataframe(flex_dist_df, hide_index=True)
        else:
            st.write("No FLEX players found")
        
        # Show team stack analysis        # Show team distribution
        teams_in_lineup = [p['team'] for p in sample_entry['lineup_detailed'] if p['team'] != 'UNK']
        if teams_in_lineup:
            team_counts = Counter(teams_in_lineup)
            st.write("**Team Stack Analysis:**")
            for team, count in team_counts.most_common():
                st.write(f"  - {team}: {count} players")
    
    # Filter data based on selection (after adding 'players' column)
    if selected_user != "All Users":
        my_entries_df = df[df['Username'] == selected_user].copy()
        num_entries = len(my_entries_df)
        st.sidebar.success(f"✅ Analyzing {num_entries} {'entry' if num_entries == 1 else 'entries'} for {selected_user}")
    else:
        my_entries_df = pd.DataFrame()  # Empty if viewing all
        st.sidebar.info("Viewing field-wide analysis")
    
    # Calculate different finish tiers for analysis
    total_entries = len(df)
    
    # Top 0.1% (minimum 5 entries)
    top_01_pct_count = max(5, int(total_entries * 0.001))
    top_01_pct = df.nsmallest(top_01_pct_count, 'Rank')
    
    # Top 1% (minimum 10 entries)
    top_1_pct_count = max(10, int(total_entries * 0.01))
    top_1_pct = df.nsmallest(top_1_pct_count, 'Rank')
    
    # Top 10% (minimum 50 entries)
    top_10_pct_count = max(50, int(total_entries * 0.10))
    top_10_pct = df.nsmallest(top_10_pct_count, 'Rank')
    
    # Use top 0.1% as primary "winners" for most analyses
    top_finishers = top_01_pct
    
    # Show contest size metrics
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Contest Tiers")
    st.sidebar.metric("Total Entries", f"{total_entries:,}")
    st.sidebar.write(f"**Top 0.1%:** {top_01_pct_count:,} entries")
    st.sidebar.write(f"**Top 1%:** {top_1_pct_count:,} entries")
    st.sidebar.write(f"**Top 10%:** {top_10_pct_count:,} entries")
    
    # Calculate leverage
    player_stats['leverage'] = (
        (player_stats['FPTS'] - player_stats['FPTS'].mean()) / 
        (player_stats['Own%'] + 1)
    )
    
    # --------------------------------------------------------
    # Analyze Winners' Player Usage Across All Tiers
    # --------------------------------------------------------
    
    # Analyze Top 0.1%
    all_winner_players_01 = []
    for players in top_01_pct['players']:
        all_winner_players_01.extend(players)
    winner_counts_01 = Counter(all_winner_players_01)
    
    # Analyze Top 1%
    all_winner_players_1 = []
    for players in top_1_pct['players']:
        all_winner_players_1.extend(players)
    winner_counts_1 = Counter(all_winner_players_1)
    
    # Analyze Top 10%
    all_winner_players_10 = []
    for players in top_10_pct['players']:
        all_winner_players_10.extend(players)
    winner_counts_10 = Counter(all_winner_players_10)
    
    # Create comprehensive analysis dataframe
    analysis_df = player_stats.copy()
    
    # Add Top 0.1% stats
    analysis_df['top_01_count'] = analysis_df['Player'].map(winner_counts_01).fillna(0).astype(int)
    analysis_df['top_01_own%'] = (analysis_df['top_01_count'] / top_01_pct_count) * 100
    
    # Add Top 1% stats
    analysis_df['top_1_count'] = analysis_df['Player'].map(winner_counts_1).fillna(0).astype(int)
    analysis_df['top_1_own%'] = (analysis_df['top_1_count'] / top_1_pct_count) * 100
    
    # Add Top 10% stats
    analysis_df['top_10_count'] = analysis_df['Player'].map(winner_counts_10).fillna(0).astype(int)
    analysis_df['top_10_own%'] = (analysis_df['top_10_count'] / top_10_pct_count) * 100
    
    # Calculate leverage for each tier
    analysis_df['top_01_leverage'] = analysis_df['top_01_own%'] - analysis_df['Own%']
    analysis_df['top_1_leverage'] = analysis_df['top_1_own%'] - analysis_df['Own%']
    analysis_df['top_10_leverage'] = analysis_df['top_10_own%'] - analysis_df['Own%']
    
    # Keep legacy columns for backwards compatibility (using Top 0.1%)
    analysis_df['winner_count'] = analysis_df['top_01_count']
    analysis_df['winner_own%'] = analysis_df['top_01_own%']
    analysis_df['winner_leverage'] = analysis_df['top_01_leverage']
    
    # Use top 0.1% as primary for most displays
    top_finishers = top_01_pct
    
    # --------------------------------------------------------
    # Tabs
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
        st.header("📊 Field Ownership Distribution")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Players", len(player_stats))
        with col2:
            avg_own = player_stats['Own%'].mean()
            st.metric("Average Ownership", f"{avg_own:.1f}%")
        with col3:
            top_owned = player_stats.nlargest(1, 'Own%')['Player'].values[0]
            st.metric("Highest Owned", top_owned)
        
        # Ownership histogram
        fig = px.histogram(
            player_stats, 
            x='Own%', 
            nbins=30,
            title="Ownership Distribution",
            labels={'Own%': 'Ownership %', 'count': 'Number of Players'}
        )
        st.plotly_chart(fig, width='stretch')
        
        # Top scorers
        st.subheader("🔥 Top 10 Scorers")
        top_scorers = player_stats.nlargest(10, 'FPTS')[['Player', 'Position', 'FPTS', 'Own%']]
        st.dataframe(top_scorers, width='stretch')
        
        # Ownership vs Performance scatter
        st.subheader("Ownership vs Performance")
        fig = px.scatter(
            player_stats,
            x='Own%',
            y='FPTS',
            hover_data=['Player', 'Position'],
            title="Ownership % vs Fantasy Points",
            labels={'Own%': 'Ownership %', 'FPTS': 'Fantasy Points'}
        )
        st.plotly_chart(fig, width='stretch')
    
    # --------------------------------------------------------
    # TAB 2: Leverage Report
    # --------------------------------------------------------
    with tab2:
        st.header("🎯 Leverage Analysis")
        
        st.markdown("""
        **Leverage Score** = (FPTS - Avg FPTS) / (Own% + 1)
        
        High leverage players outperformed relative to their ownership - these were the key differentiators.
        """)
        
        # Tier Comparison
        st.subheader("📊 Ownership Comparison Across Finish Tiers")
        
        # Select top players by FPTS to compare
        top_players_for_comparison = analysis_df.nlargest(20, 'FPTS')
        
        comparison_data = []
        for _, player_row in top_players_for_comparison.iterrows():
            comparison_data.append({
                'Player': player_row['Player'],
                'Position': player_row['Position'],
                'FPTS': round(player_row['FPTS'], 1),
                'Field Own%': round(player_row['Own%'], 1),
                'Top 0.1% Own%': round(player_row['top_01_own%'], 1),
                'Top 1% Own%': round(player_row['top_1_own%'], 1),
                'Top 10% Own%': round(player_row['top_10_own%'], 1),
                'Top 0.1% Lev': round(player_row['top_01_leverage'], 1),
                'Top 1% Lev': round(player_row['top_1_leverage'], 1),
                'Top 10% Lev': round(player_row['top_10_leverage'], 1)
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        st.dataframe(
            comparison_df.style.background_gradient(
                subset=['Top 0.1% Lev', 'Top 1% Lev', 'Top 10% Lev'],
                cmap='RdYlGn',
                vmin=-20,
                vmax=20
            ).format({
                'FPTS': '{:.1f}',
                'Field Own%': '{:.1f}',
                'Top 0.1% Own%': '{:.1f}',
                'Top 1% Own%': '{:.1f}',
                'Top 10% Own%': '{:.1f}',
                'Top 0.1% Lev': '{:.1f}',
                'Top 1% Lev': '{:.1f}',
                'Top 10% Lev': '{:.1f}'
            }),
            width='stretch',
            hide_index=True
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("✅ Positive Leverage (Winners' Edge)")
            positive_lev = analysis_df[analysis_df['leverage'] > 0].nlargest(15, 'leverage')
            st.dataframe(
                positive_lev[['Player', 'Position', 'FPTS', 'Own%', 'leverage', 'winner_own%']].round(1),
                width='stretch',
                hide_index=True
            )
        
        with col2:
            st.subheader("❌ Negative Leverage (Field Traps)")
            negative_lev = analysis_df[(analysis_df['leverage'] < 0) & (analysis_df['Own%'] > 0.1)].nsmallest(15, 'leverage')
            st.dataframe(
                negative_lev[['Player', 'Position', 'FPTS', 'Own%', 'leverage', 'winner_own%']].round(1),
                width='stretch',
                hide_index=True
            )
        
        # Winner leverage
        st.subheader("🏆 Top 0.1% Leverage vs Field")
        fig = px.scatter(
            analysis_df[analysis_df['winner_count'] > 0],
            x='Own%',
            y='winner_own%',
            size='FPTS',
            hover_data=['Player', 'Position', 'leverage'],
            title="Field Ownership vs Top 0.1% Ownership",
            labels={'Own%': 'Field Ownership %', 'winner_own%': "Top 0.1% Ownership %"}
        )
        # Add diagonal line (equal ownership)
        max_own = max(analysis_df['Own%'].max(), analysis_df['winner_own%'].max())
        fig.add_trace(go.Scatter(
            x=[0, max_own], y=[0, max_own],
            mode='lines', line=dict(dash='dash', color='gray'),
            name='Equal Ownership'
        ))
        st.plotly_chart(fig, width='stretch')
    
    # --------------------------------------------------------
    # TAB 3: Stack Analysis
    # --------------------------------------------------------
    with tab3:
        st.header("🧱 Stack Construction Analysis")
        
        # Analyze winners' stacks using detailed lineup data
        st.subheader("🏆 Winners' Stack Distribution")
        
        # Analyze each top finishing lineup
        stack_analysis = []
        
        for idx, row in top_finishers.iterrows():
            lineup_detailed = row['lineup_detailed']
            
            # Extract teams from lineup
            player_teams = [p['team'] for p in lineup_detailed if p['team'] != 'UNK']
            
            if player_teams:
                team_counts = Counter(player_teams)
                
                # Find primary stack
                primary_team, primary_count = team_counts.most_common(1)[0]
                
                stack_analysis.append({
                    'lineup_idx': idx,
                    'primary_team': primary_team,
                    'stack_size': primary_count,
                    'unique_teams': len(team_counts),
                    'all_teams': dict(team_counts)
                })
            else:
                # No team info available
                stack_analysis.append({
                    'lineup_idx': idx,
                    'primary_team': 'UNK',
                    'stack_size': 0,
                    'unique_teams': 0,
                    'all_teams': {}
                })
        
        stack_df = pd.DataFrame(stack_analysis)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Stack size distribution
            stack_dist = stack_df['stack_size'].value_counts().sort_index()
            fig = px.bar(
                x=stack_dist.index,
                y=stack_dist.values,
                title="Primary Stack Size Distribution",
                labels={'x': 'Number of Players from Same Team', 'y': 'Number of Lineups'}
            )
            st.plotly_chart(fig, width='stretch')
        
        with col2:
            # Team diversity
            team_div = stack_df['unique_teams'].value_counts().sort_index()
            fig = px.bar(
                x=team_div.index,
                y=team_div.values,
                title="Team Diversity Distribution",
                labels={'x': 'Number of Different Teams', 'y': 'Number of Lineups'}
            )
            st.plotly_chart(fig, width='stretch')
        
        # Most popular stacks
        st.subheader("Most Common Primary Stacks in Winning Lineups")
        if 'primary_team' in stack_df.columns:
            # Filter out 'UNK' teams
            valid_stacks = stack_df[stack_df['primary_team'] != 'UNK']
            if len(valid_stacks) > 0:
                team_stack_counts = valid_stacks['primary_team'].value_counts().head(10)
                
                # Create display dataframe
                stack_display = pd.DataFrame({
                    'Team': team_stack_counts.index,
                    'Count': team_stack_counts.values
                })
                st.dataframe(stack_display, width='stretch', hide_index=True)
            else:
                st.info("No team data available. Upload player stats with Team column to see team-based analysis.")
        
        # Position-based stack breakdown
        st.subheader("Stack Position Composition")
        st.caption("Analyzing which positions make up the primary stacks in winning lineups")
        
        position_stacks = []
        for idx, row in top_finishers.iterrows():
            lineup_detailed = row['lineup_detailed']
            
            # Group by team
            team_players = {}
            for player_info in lineup_detailed:
                team = player_info['team']
                if team != 'UNK':
                    if team not in team_players:
                        team_players[team] = []
                    team_players[team].append(player_info)
            
            # Find primary stack composition
            if team_players:
                primary_team = max(team_players.items(), key=lambda x: len(x[1]))
                positions = [p['position'] for p in primary_team[1]]
                position_str = '+'.join(sorted(positions))
                
                position_stacks.append({
                    'team': primary_team[0],
                    'positions': position_str,
                    'stack_size': len(positions)
                })
        
        if position_stacks:
            pos_stack_df = pd.DataFrame(position_stacks)
            pos_composition = pos_stack_df['positions'].value_counts().head(10)
            
            st.dataframe(
                pd.DataFrame({'Stack Composition': pos_composition.index, 'Count': pos_composition.values}),
                width='stretch',
                hide_index=True
            )
        
        # FLEX Position Analysis
        st.subheader("🔄 FLEX Position Distribution")
        st.caption("Analyzing which positions (RB/WR/TE) were used in the FLEX spot")
        
        # Collect all FLEX players from top finishers
        flex_players_winners = []
        for idx, row in top_finishers.iterrows():
            lineup_detailed = row['lineup_detailed']
            for player_info in lineup_detailed:
                if player_info.get('is_flex', False):
                    flex_players_winners.append(player_info)
        
        # Collect all FLEX players from entire field
        flex_players_field = []
        for idx, row in df.iterrows():
            lineup_detailed = row['lineup_detailed']
            for player_info in lineup_detailed:
                if player_info.get('is_flex', False):
                    flex_players_field.append(player_info)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Winners' FLEX Distribution:**")
            if flex_players_winners:
                winner_flex_pos = [p['actual_position'] for p in flex_players_winners]
                winner_flex_counter = Counter(winner_flex_pos)
                winner_flex_total = len(winner_flex_pos)
                
                winner_flex_df = pd.DataFrame([
                    {
                        'Position': pos, 
                        'Count': count, 
                        'Percentage': f"{(count/winner_flex_total)*100:.1f}%"
                    }
                    for pos, count in winner_flex_counter.most_common()
                ])
                st.dataframe(winner_flex_df, hide_index=True, width='stretch')
            else:
                st.info("No FLEX data available")
        
        with col2:
            st.write("**Field FLEX Distribution:**")
            if flex_players_field:
                field_flex_pos = [p['actual_position'] for p in flex_players_field]
                field_flex_counter = Counter(field_flex_pos)
                field_flex_total = len(field_flex_pos)
                
                field_flex_df = pd.DataFrame([
                    {
                        'Position': pos, 
                        'Count': count, 
                        'Percentage': f"{(count/field_flex_total)*100:.1f}%"
                    }
                    for pos, count in field_flex_counter.most_common()
                ])
                st.dataframe(field_flex_df, hide_index=True, width='stretch')
            else:
                st.info("No FLEX data available")
    
    # --------------------------------------------------------
    # TAB 4: My Performance
    # --------------------------------------------------------
    with tab4:
        st.header("📈 My Contest Performance")
        
        if selected_user != "All Users" and len(my_entries_df) > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Entries", len(my_entries_df))
            with col2:
                best_rank = my_entries_df['Rank'].min()
                st.metric("Best Finish", f"#{best_rank:,.0f}")
            with col3:
                avg_score = my_entries_df['Points'].mean()
                st.metric("Avg Score", f"{avg_score:.1f}")
            with col4:
                top_score = my_entries_df['Points'].max()
                st.metric("Top Score", f"{top_score:.1f}")
            
            # Portfolio-level analysis
            st.subheader("📊 Portfolio Analysis")
            
            # Calculate my ownership vs field for each player
            my_all_players = []
            for players in my_entries_df['players']:
                my_all_players.extend(players)
            
            my_player_counts = Counter(my_all_players)
            my_total_lineups = len(my_entries_df)
            
            # Create ownership comparison
            my_ownership_df = pd.DataFrame([
                {
                    'Player': player,
                    'My Count': count,
                    'My Own%': (count / my_total_lineups) * 100
                }
                for player, count in my_player_counts.items()
            ])
            
            # Merge with field ownership
            portfolio_df = my_ownership_df.merge(
                analysis_df[['Player', 'Position', 'FPTS', 'Own%', 'top_01_own%', 'leverage']],
                on='Player',
                how='left'
            )
            
            portfolio_df['Own% Diff'] = portfolio_df['My Own%'] - portfolio_df['Own%']
            portfolio_df['Top 0.1% Diff'] = portfolio_df['My Own%'] - portfolio_df['top_01_own%']
            
            col1, col2 = st.columns(2)
            
            with col1:
                avg_my_own = portfolio_df['My Own%'].mean()
                avg_field_own = portfolio_df['Own%'].mean()
                st.metric(
                    "Avg Ownership per Player",
                    f"{avg_my_own:.1f}%",
                    delta=f"{avg_my_own - avg_field_own:.1f}% vs field",
                    help="Higher = More concentrated portfolio, Lower = More diversified"
                )
            
            with col2:
                avg_my_score = portfolio_df['FPTS'].mean()
                avg_field_score = player_stats['FPTS'].mean()
                st.metric(
                    "Avg Player Points",
                    f"{avg_my_score:.1f}",
                    delta=f"{avg_my_score - avg_field_score:.1f} vs field"
                )
            
            # My exposure heatmap
            st.subheader("🔥 My Player Exposure vs Field")
            st.caption("Positive = Overweight, Negative = Underweight")
            
            exposure_table = portfolio_df.nlargest(20, 'My Count')[
                ['Player', 'Position', 'My Own%', 'Own%', 'Own% Diff', 'FPTS', 'leverage']
            ].round(1)
            
            st.dataframe(
                exposure_table.style.background_gradient(
                    subset=['Own% Diff'],
                    cmap='RdYlGn',
                    vmin=-30,
                    vmax=30
                ),
                width='stretch',
                hide_index=True
            )
            
            # Best and Worst Lineups
            st.subheader("🏆 Best Lineups")
            best_lineups = my_entries_df.nsmallest(5, 'Rank')[['Rank', 'Points', 'Lineup']]
            st.dataframe(best_lineups, width='stretch', hide_index=True)
            
            st.subheader("📉 Worst Lineups")
            worst_lineups = my_entries_df.nlargest(5, 'Rank')[['Rank', 'Points', 'Lineup']]
            st.dataframe(worst_lineups, width='stretch', hide_index=True)
            
            # Lineup duplication check
            st.subheader("🔄 Lineup Duplication Analysis")
            lineup_counts = my_entries_df['Lineup'].value_counts()
            duplicated = lineup_counts[lineup_counts > 1]
            
            if len(duplicated) > 0:
                st.warning(f"⚠️ Found {len(duplicated)} duplicated lineups across {duplicated.sum()} entries")
                st.dataframe(
                    pd.DataFrame({
                        'Lineup': duplicated.index,
                        'Count': duplicated.values
                    }),
                    width='stretch',
                    hide_index=True
                )
            else:
                st.success("✅ No duplicate lineups found - good lineup diversity!")
            
            # Score distribution
            st.subheader("📈 Score Distribution")
            fig = px.histogram(
                my_entries_df,
                x='Points',
                nbins=20,
                title="My Lineup Score Distribution"
            )
            st.plotly_chart(fig, width='stretch')
            
            # Player overlap with winners
            st.subheader("🎯 My Player Overlap with Winners")
            
            my_all_players = []
            for players in my_entries_df['players']:
                my_all_players.extend(players)
            
            my_player_counts = Counter(my_all_players)
            
            overlap_data = []
            for player, my_count in my_player_counts.items():
                winner_count = winner_counts_01.get(player, 0)
                overlap_data.append({
                    'Player': player,
                    'My Usage': my_count,
                    'Top 0.1% Usage': winner_count,
                    'Overlap': 'Yes' if winner_count > 0 else 'No'
                })
            
            overlap_df = pd.DataFrame(overlap_data).sort_values('Top 0.1% Usage', ascending=False)
            st.dataframe(overlap_df.head(20), width='stretch')
        else:
            st.info("Select a user from the sidebar to view individual performance")
    
    # --------------------------------------------------------
    # TAB 5: Boom/Bust Accuracy
    # --------------------------------------------------------
    with tab5:
        st.header("🔬 Projection Accuracy Analysis")
        
        if roo_file:
            boom_bust_df = roo_df.copy()
            
            # Merge with actual results from contest
            accuracy_df = boom_bust_df.merge(
                player_stats[['Player', 'FPTS', 'Own%']], 
                on='Player', 
                how='inner'
            )
            
            if len(accuracy_df) > 0:
                # ROO projections use OWS_Median_Proj, Floor_Proj, Ceiling_Proj
                proj_col = 'OWS_Median_Proj'
                floor_col = 'Floor_Proj'
                ceil_col = 'Ceiling_Proj'
                
                # Calculate projection errors
                accuracy_df['proj_error'] = accuracy_df['FPTS'] - accuracy_df[proj_col]
                accuracy_df['proj_error_pct'] = (accuracy_df['proj_error'] / (accuracy_df[proj_col] + 0.1)) * 100
                
                # Identify boom/bust outcomes
                accuracy_df['hit_ceiling'] = accuracy_df['FPTS'] >= accuracy_df[ceil_col]
                accuracy_df['hit_floor'] = accuracy_df['FPTS'] <= accuracy_df[floor_col]
                accuracy_df['in_range'] = ~accuracy_df['hit_ceiling'] & ~accuracy_df['hit_floor']
                
                # Calculate metrics
                mae = accuracy_df['proj_error'].abs().mean()
                rmse = np.sqrt((accuracy_df['proj_error'] ** 2).mean())
                boom_rate = (accuracy_df['hit_ceiling'].sum() / len(accuracy_df)) * 100
                bust_rate = (accuracy_df['hit_floor'].sum() / len(accuracy_df)) * 100
                
                # Determine RAG status for each metric
                def get_rag_color(value, metric_type):
                    """Return color based on metric performance"""
                    if metric_type == 'mae':
                        if value < 3: return '🟢'
                        elif value < 4: return '🟡'
                        else: return '🔴'
                    elif metric_type == 'rmse':
                        if value < 4: return '🟢'
                        elif value < 5: return '🟡'
                        else: return '🔴'
                    elif metric_type == 'ceiling':
                        if 5 <= value <= 15: return '🟢'
                        elif value > 15: return '🟡'
                        else: return '🔴'
                    elif metric_type == 'floor':
                        if 20 <= value <= 40: return '🟢'
                        elif value > 40: return '🔴'
                        else: return '🟡'
                    return '⚪'
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    rag_mae = get_rag_color(mae, 'mae')
                    st.metric(
                        f"{rag_mae} Mean Absolute Error", 
                        f"{mae:.2f} pts",
                        help="Average error in points. Lower is better. 🟢<3, 🟡<4, 🔴≥4"
                    )
                with col2:
                    rag_rmse = get_rag_color(rmse, 'rmse')
                    st.metric(
                        f"{rag_rmse} RMSE", 
                        f"{rmse:.2f} pts",
                        help="Root Mean Square Error - penalizes large errors. 🟢<4, 🟡<5, 🔴≥5"
                    )
                with col3:
                    rag_ceiling = get_rag_color(boom_rate, 'ceiling')
                    st.metric(
                        f"{rag_ceiling} Ceiling Hit Rate", 
                        f"{boom_rate:.1f}%",
                        help="% who exceeded ceiling. 🟢5-15%, 🟡>15% (high variance), 🔴<5% (low scoring)"
                    )
                with col4:
                    rag_floor = get_rag_color(bust_rate, 'floor')
                    st.metric(
                        f"{rag_floor} Floor Hit Rate", 
                        f"{bust_rate:.1f}%",
                        help="% who fell below floor. 🟢20-40%, 🔴>40% (many busts), 🟡<20% (exceeded)"
                    )
                
                # Generate contextual commentary
                commentary = []
                
                # MAE commentary
                if mae < 3:
                    commentary.append("✅ **Excellent projection accuracy** - Your median projections were very close to actual outcomes.")
                elif mae < 4:
                    commentary.append("👍 **Good projection accuracy** - Your projections tracked well with actual scoring.")
                else:
                    commentary.append("⚠️ **Projection accuracy needs work** - Consider refining your projection methodology or data sources.")
                
                # RMSE commentary
                if rmse < 4:
                    commentary.append("✅ **Low variance in errors** - Your projections consistently hit the mark without large outliers.")
                elif rmse < 5:
                    commentary.append("👍 **Moderate variance** - Mostly accurate with some larger misses on outlier performances.")
                else:
                    commentary.append("⚠️ **High error variance** - You had some major misses. Focus on identifying which player types you're misjudging.")
                
                # Ceiling commentary
                if boom_rate > 15:
                    commentary.append(f"🔥 **High variance slate** ({boom_rate:.0f}% ceiling hits) - More players exceeded expectations than usual. This creates GPP opportunities but makes cash games riskier.")
                elif boom_rate >= 5:
                    commentary.append(f"✅ **Normal variance** ({boom_rate:.0f}% ceiling hits) - The slate played out as expected with typical upside hitting.")
                else:
                    commentary.append(f"❄️ **Low scoring slate** ({boom_rate:.0f}% ceiling hits) - Few players exceeded ceilings. Chalk likely won, favoring cash game strategies.")
                
                # Floor commentary
                if bust_rate > 40:
                    commentary.append(f"💥 **Bust-heavy slate** ({bust_rate:.0f}% floor hits) - Many players underperformed. Lineup construction and game script reads were critical to success.")
                elif bust_rate >= 20:
                    commentary.append(f"✅ **Expected bust rate** ({bust_rate:.0f}% floor hits) - Normal amount of underperformers. Your floor projections were well-calibrated.")
                else:
                    commentary.append(f"🎯 **Players overperformed** ({bust_rate:.0f}% floor hits) - Fewer busts than expected. High-floor plays likely won, favoring safer roster construction.")
                
                # Correlation analysis
                if boom_rate > 15 and bust_rate > 40:
                    commentary.append("⚡ **High volatility slate** - Both booms and busts exceeded expectations. Tournament winners likely needed both luck and leverage on the right variance plays.")
                elif boom_rate < 10 and bust_rate < 25:
                    commentary.append("📊 **Stable scoring environment** - Outcomes clustered near projections. This favored optimal lineup construction over taking chances on leverage plays.")
                
                st.markdown("### 💡 So What? - Key Takeaways")
                for comment in commentary:
                    st.markdown(comment)
                
                # Projection accuracy scatter
                fig = px.scatter(
                    accuracy_df,
                    x=proj_col,
                    y='FPTS',
                    color='Position',
                    hover_data=['Player', 'Team'],
                    title="Projected vs Actual Fantasy Points",
                    labels={proj_col: 'Projected Points', 'FPTS': 'Actual Points'}
                )
                max_pts = max(accuracy_df[proj_col].max(), accuracy_df['FPTS'].max())
                fig.add_trace(go.Scatter(
                    x=[0, max_pts], y=[0, max_pts],
                    mode='lines', line=dict(dash='dash', color='gray'),
                    name='Perfect Projection',
                    showlegend=False
                ))
                st.plotly_chart(fig, width='stretch')
                
                # Show biggest misses
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📈 Biggest Positive Surprises")
                    over_performers = accuracy_df.nlargest(10, 'proj_error')
                    st.dataframe(
                        over_performers[['Player', 'Position', proj_col, 'FPTS', 'proj_error', 'Own%']],
                        width='stretch',
                        hide_index=True
                    )
                with col2:
                    st.subheader("📉 Biggest Busts")
                    under_performers = accuracy_df.nsmallest(10, 'proj_error')
                    st.dataframe(
                        under_performers[['Player', 'Position', proj_col, 'FPTS', 'proj_error', 'Own%']],
                        width='stretch',
                        hide_index=True
                    )
                
                # Boom/Bust breakdown by position
                st.subheader("💥 Boom/Bust Breakdown by Position")
                position_analysis = accuracy_df.groupby('Position').agg({
                    'hit_ceiling': 'sum',
                    'hit_floor': 'sum',
                    'in_range': 'sum',
                    'Player': 'count'
                }).rename(columns={'Player': 'total'})
                
                position_analysis['ceiling_rate'] = (position_analysis['hit_ceiling'] / position_analysis['total']) * 100
                position_analysis['floor_rate'] = (position_analysis['hit_floor'] / position_analysis['total']) * 100
                position_analysis['in_range_rate'] = (position_analysis['in_range'] / position_analysis['total']) * 100
                
                st.dataframe(
                    position_analysis[['total', 'ceiling_rate', 'in_range_rate', 'floor_rate']].round(1),
                    width='stretch'
                )
            else:
                st.warning("No matching players found between ROO projections and contest results")
        else:
            st.info("👆 Upload ROO Projections CSV in the sidebar to analyze accuracy")
    
    # --------------------------------------------------------
    # TAB 6: ROI Tracker
    # --------------------------------------------------------
    with tab6:
        st.header("💰 ROI & Profit Tracking")
        
        if selected_user == "All Users" or len(my_entries_df) == 0:
            st.info("Select a user from the sidebar to calculate ROI")
        else:
            st.markdown("### Contest Settings")
            col1, col2, col3 = st.columns(3)
            with col1:
                entry_fee = st.number_input("Entry Fee ($)", value=20, min_value=1)
            with col2:
                total_entries = len(my_entries_df)
                st.metric("Your Total Entries", total_entries)
            with col3:
                prize_pool = st.number_input("Total Prize Pool ($)", value=20000, min_value=0)
            
            total_invested = entry_fee * total_entries
            
            # Define payout structure
            st.markdown("### Payout Structure")
            payout_structure = st.text_area(
                "Enter payout structure (Rank: Prize per line)",
                value="1: 4000\n2: 1750\n3: 1000\n4-5: 500\n6-10: 250\n11-20: 100\n21-50: 50\n51-100: 30\n101-415: 25\n416-1046: 20",
                height=200
            )
            
            # Parse payout structure
            payouts = {}
            for line in payout_structure.strip().split('\n'):
                if ':' in line:
                    rank_part, prize_part = line.split(':')
                    prize = float(prize_part.strip().replace('$', '').replace(',', ''))
                    
                    if '-' in rank_part:
                        start, end = rank_part.split('-')
                        for r in range(int(start), int(end) + 1):
                            payouts[r] = prize
                    else:
                        payouts[int(rank_part.strip())] = prize
            
            # Calculate winnings
            my_entries_df['Prize'] = my_entries_df['Rank'].map(payouts).fillna(0)
            total_winnings = my_entries_df['Prize'].sum()
            net_profit = total_winnings - total_invested
            roi = (net_profit / total_invested) * 100 if total_invested > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Invested", f"${total_invested:,.2f}")
            with col2:
                st.metric("Total Winnings", f"${total_winnings:,.2f}")
            with col3:
                st.metric("Net Profit", f"${net_profit:,.2f}", delta=f"{roi:.1f}% ROI")
            with col4:
                cashes = (my_entries_df['Prize'] > 0).sum()
                cash_rate = (cashes / len(my_entries_df)) * 100
                st.metric("Cash Rate", f"{cash_rate:.1f}%", delta=f"{cashes}/{len(my_entries_df)}")
            
            # Show cashing lineups
            st.subheader("💵 Cashing Lineups")
            cashing = my_entries_df[my_entries_df['Prize'] > 0].sort_values('Prize', ascending=False)
            if len(cashing) > 0:
                st.dataframe(cashing[['Rank', 'Prize', 'Points', 'Lineup']], width='stretch')
            else:
                st.info("No lineups cashed in this contest")
    
    # --------------------------------------------------------
    # TAB 7: Post-Contest Simulator
    # --------------------------------------------------------
    with tab7:
        st.header("🎲 Remove Variance with Monte Carlo")
        
        st.markdown("""
        **Purpose:** Run your lineups through thousands of simulations to determine:
        - Which lineups were objectively good/bad (not just lucky/unlucky)
        - Which players were good/bad plays regardless of actual outcome
        - Your true expected ROI after removing single-game variance
        """)
        
        st.info("🚧 Feature coming soon - will integrate with pre-contest simulator methodology")
        
        st.markdown("""
        **How it will work:**
        1. Use your pre-contest projections (ceiling, floor, stddev)
        2. Simulate the slate 5000+ times
        3. Calculate average finish for each of your lineups
        4. Calculate average ROI for each player
        5. Compare simulated results vs actual results
        6. Identify lucky/unlucky outcomes
        
        **Key Metrics:**
        - **Sim Lineup ROI:** Expected ROI across all scenarios
        - **Sim Player ROI:** Player value independent of game script
        - **Variance Impact:** How much luck influenced your results
        - **Process Quality:** Were your decisions good regardless of outcome?
        """)

else:
    st.info("👆 Upload your DraftKings contest results CSV to begin analysis")
    
    st.markdown("""
    ### How to Get Your Contest Results:
    
    1. Go to DraftKings.com
    2. Navigate to **My Contests** → Select your completed contest
    3. Click **Export Results** (downloads CSV with all entries)
    4. Upload the CSV file using the sidebar uploader
    
    ### What's Included in the Analysis:
    
    - **📊 Ownership Analysis** - Field ownership distribution and top scorers
    - **🎯 Leverage Report** - Identify positive/negative leverage plays
    - **🧱 Stack Analysis** - Winning lineup construction patterns
    - **📈 My Performance** - Your entries vs field (select your username)
    - **🔬 Boom/Bust Accuracy** - Compare projections to actual (optional upload)
    - **💰 ROI Tracker** - Calculate profit/loss with payout structure
    - **🎲 Post-Contest Simulator** - Coming soon
    """)

