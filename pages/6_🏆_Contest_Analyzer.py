import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import itertools

st.title("🏆 DFS Contest Analyzer")

st.info("📊 **Post-Contest Analysis Tool** - Upload your contest results to analyze performance, leverage, stacks, and identify areas for improvement.")

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
        st.error("❌ Could not find ownership column")
        st.stop()
        
    if fpts_col and fpts_col != 'FPTS':
        ownership_df['FPTS'] = ownership_df[fpts_col]
    elif not fpts_col:
        st.error("❌ Could not find fantasy points column")
        st.stop()
        
    if salary_col and salary_col != 'Salary':
        ownership_df['Salary'] = ownership_df[salary_col]
        
    if position_col and position_col != 'position':
        ownership_df['position'] = ownership_df[position_col]
    
    # --------------------------------------------------------
    # Parse Winners and My Entries Lineups
    # --------------------------------------------------------
    
    def parse_lineup(lineup_str):
        """Parse lineup string into list of player names"""
        if pd.isna(lineup_str):
            return []
        # Handle various formats: "QB WR WR RB" or just names separated by spaces
        players = str(lineup_str).strip().split()
        # Filter out position abbreviations
        positions = ['QB', 'RB', 'WR', 'TE', 'DST', 'FLEX', 'D']
        return [p for p in players if p.upper() not in positions]
    
    # Detect lineup column
    winners_lineup_col = find_column(winners_df, ['lineup', 'players', 'roster'])
    my_lineup_col = find_column(my_entries_df, ['lineup', 'players', 'roster'])
    
    if winners_lineup_col:
        winners_df['players'] = winners_df[winners_lineup_col].apply(parse_lineup)
    else:
        st.error("❌ Could not find lineup column in winners file")
        st.stop()
        
    if my_lineup_col:
        my_entries_df['players'] = my_entries_df[my_lineup_col].apply(parse_lineup)
    else:
        st.error("❌ Could not find lineup column in my entries file")
        st.stop()
    
    # --------------------------------------------------------
    # Calculate Leverage Scores
    # --------------------------------------------------------
    
    ownership_df['leverage'] = (ownership_df['FPTS'] - ownership_df['FPTS'].mean()) / (ownership_df['Own%'] + 1)
    
    # --------------------------------------------------------
    # Analyze Winners' Player Usage
    # --------------------------------------------------------
    
    all_winner_players = []
    for players in winners_df['players']:
        all_winner_players.extend(players)
    
    winner_player_counts = Counter(all_winner_players)
    total_winner_lineups = len(winners_df)
    
    winner_usage_df = pd.DataFrame([
        {'name': player, 'winner_count': count, 'winner_own%': (count / total_winner_lineups) * 100}
        for player, count in winner_player_counts.items()
    ])
    
    # Merge with ownership data
    analysis_df = ownership_df.merge(winner_usage_df, on='name', how='left')
    analysis_df['winner_own%'] = analysis_df['winner_own%'].fillna(0)
    analysis_df['winner_count'] = analysis_df['winner_count'].fillna(0).astype(int)
    
    # Calculate winner leverage
    analysis_df['winner_leverage'] = analysis_df['winner_own%'] - analysis_df['Own%']
    
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
            st.metric("Total Players", len(ownership_df))
        with col2:
            avg_own = ownership_df['Own%'].mean()
            st.metric("Average Ownership", f"{avg_own:.1f}%")
        with col3:
            top_owned = ownership_df.nlargest(1, 'Own%')['name'].values[0]
            st.metric("Highest Owned", top_owned)
        
        # Ownership histogram
        fig = px.histogram(
            ownership_df, 
            x='Own%', 
            nbins=30,
            title="Ownership Distribution",
            labels={'Own%': 'Ownership %', 'count': 'Number of Players'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Top scorers
        st.subheader("🔥 Top 10 Scorers")
        top_scorers = ownership_df.nlargest(10, 'FPTS')[['name', 'position', 'FPTS', 'Own%', 'Salary']]
        st.dataframe(top_scorers, use_container_width=True)
        
        # Ownership vs Performance scatter
        st.subheader("Ownership vs Performance")
        fig = px.scatter(
            ownership_df,
            x='Own%',
            y='FPTS',
            hover_data=['name', 'position'],
            title="Ownership % vs Fantasy Points",
            labels={'Own%': 'Ownership %', 'FPTS': 'Fantasy Points'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # --------------------------------------------------------
    # TAB 2: Leverage Report
    # --------------------------------------------------------
    with tab2:
        st.header("🎯 Leverage Analysis")
        
        st.markdown("""
        **Leverage Score** = (FPTS - Avg FPTS) / (Own% + 1)
        
        High leverage players outperformed relative to their ownership - these were the key differentiators.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("✅ Positive Leverage (Winners' Edge)")
            positive_lev = analysis_df[analysis_df['leverage'] > 0].nlargest(15, 'leverage')
            st.dataframe(
                positive_lev[['name', 'position', 'FPTS', 'Own%', 'leverage', 'winner_own%']],
                use_container_width=True
            )
        
        with col2:
            st.subheader("❌ Negative Leverage (Field Traps)")
            negative_lev = analysis_df[analysis_df['leverage'] < 0].nsmallest(15, 'leverage')
            st.dataframe(
                negative_lev[['name', 'position', 'FPTS', 'Own%', 'leverage', 'winner_own%']],
                use_container_width=True
            )
        
        # Winner leverage
        st.subheader("🏆 Winners' Leverage vs Field")
        fig = px.scatter(
            analysis_df[analysis_df['winner_count'] > 0],
            x='Own%',
            y='winner_own%',
            size='FPTS',
            hover_data=['name', 'position', 'leverage'],
            title="Field Ownership vs Winners' Ownership",
            labels={'Own%': 'Field Ownership %', 'winner_own%': "Winners' Ownership %"}
        )
        # Add diagonal line (equal ownership)
        max_own = max(analysis_df['Own%'].max(), analysis_df['winner_own%'].max())
        fig.add_trace(go.Scatter(
            x=[0, max_own], y=[0, max_own],
            mode='lines', line=dict(dash='dash', color='gray'),
            name='Equal Ownership'
        ))
        st.plotly_chart(fig, use_container_width=True)
    
    # --------------------------------------------------------
    # TAB 3: Stack Analysis
    # --------------------------------------------------------
    with tab3:
        st.header("🧱 Stack Construction Analysis")
        
        # Analyze winners' stacks
        st.subheader("🏆 Winners' Stack Distribution")
        
        # Get team mapping from boom_bust file if available
        if 'team' in boom_bust_df.columns and 'name' in boom_bust_df.columns:
            team_map = dict(zip(boom_bust_df['name'], boom_bust_df['team']))
        else:
            team_map = {}
        
        # Analyze each winning lineup
        stack_analysis = []
        
        for idx, row in winners_df.iterrows():
            players = row['players']
            
            # Get teams for each player
            player_teams = [team_map.get(p, 'UNK') for p in players]
            team_counts = Counter(player_teams)
            
            # Find primary stack
            if team_counts:
                primary_team, primary_count = team_counts.most_common(1)[0]
            else:
                primary_team, primary_count = 'UNK', 0
            
            stack_analysis.append({
                'lineup_idx': idx,
                'primary_team': primary_team,
                'stack_size': primary_count,
                'unique_teams': len(team_counts)
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
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Team diversity
            team_div = stack_df['unique_teams'].value_counts().sort_index()
            fig = px.bar(
                x=team_div.index,
                y=team_div.values,
                title="Team Diversity Distribution",
                labels={'x': 'Number of Different Teams', 'y': 'Number of Lineups'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Most popular stacks
        st.subheader("Most Common Game Stacks in Winning Lineups")
        if 'primary_team' in stack_df.columns:
            team_stack_counts = stack_df['primary_team'].value_counts().head(10)
            st.dataframe(team_stack_counts, use_container_width=True)
    
    # --------------------------------------------------------
    # TAB 4: My Performance
    # --------------------------------------------------------
    with tab4:
        st.header("📈 My Contest Performance")
        
        if 'Rank' in my_entries_df.columns or find_column(my_entries_df, ['rank', 'finish']):
            rank_col = 'Rank' if 'Rank' in my_entries_df.columns else find_column(my_entries_df, ['rank', 'finish'])
            points_col = find_column(my_entries_df, ['points', 'score', 'fpts'])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Entries", len(my_entries_df))
            with col2:
                if rank_col and rank_col in my_entries_df.columns:
                    best_rank = my_entries_df[rank_col].min()
                    st.metric("Best Finish", f"#{best_rank:,.0f}")
            with col3:
                if points_col and points_col in my_entries_df.columns:
                    avg_score = my_entries_df[points_col].mean()
                    st.metric("Avg Score", f"{avg_score:.1f}")
            with col4:
                if points_col and points_col in my_entries_df.columns:
                    top_score = my_entries_df[points_col].max()
                    st.metric("Top Score", f"{top_score:.1f}")
            
            # Score distribution
            if points_col and points_col in my_entries_df.columns:
                fig = px.histogram(
                    my_entries_df,
                    x=points_col,
                    nbins=20,
                    title="My Lineup Score Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Lineup results table
            st.subheader("Individual Lineup Results")
            display_cols = [col for col in [rank_col, points_col, my_lineup_col] if col and col in my_entries_df.columns]
            if display_cols:
                st.dataframe(my_entries_df[display_cols].head(20), use_container_width=True)
        else:
            st.warning("Rank/Points columns not found in My Entries file")
        
        # Player overlap with winners
        st.subheader("🎯 My Player Overlap with Winners")
        
        my_all_players = []
        for players in my_entries_df['players']:
            my_all_players.extend(players)
        
        my_player_counts = Counter(my_all_players)
        
        overlap_data = []
        for player, my_count in my_player_counts.items():
            winner_count = winner_player_counts.get(player, 0)
            overlap_data.append({
                'Player': player,
                'My Usage': my_count,
                'Winner Usage': winner_count,
                'Overlap': 'Yes' if winner_count > 0 else 'No'
            })
        
        overlap_df = pd.DataFrame(overlap_data).sort_values('Winner Usage', ascending=False)
        st.dataframe(overlap_df.head(20), use_container_width=True)
    
    # --------------------------------------------------------
    # TAB 5: Boom/Bust Accuracy
    # --------------------------------------------------------
    with tab5:
        st.header("🔬 Projection Accuracy Analysis")
        
        # Merge boom/bust projections with actual results
        if 'name' in boom_bust_df.columns:
            accuracy_df = boom_bust_df.merge(
                ownership_df[['name', 'FPTS', 'Own%']], 
                on='name', 
                how='inner'
            )
            
            # Find projection columns
            proj_col = find_column(accuracy_df, ['proj', 'projection', 'proj_adj'])
            ceil_col = find_column(accuracy_df, ['ceiling', 'ceil', 'ceiling_adj'])
            boom_col = find_column(accuracy_df, ['boom%', 'boom_prob', 'boom'])
            
            if proj_col and proj_col in accuracy_df.columns:
                accuracy_df['proj_error'] = accuracy_df['FPTS'] - accuracy_df[proj_col]
                accuracy_df['proj_error_pct'] = (accuracy_df['proj_error'] / accuracy_df[proj_col]) * 100
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    mae = accuracy_df['proj_error'].abs().mean()
                    st.metric("Mean Absolute Error", f"{mae:.2f} pts")
                with col2:
                    rmse = np.sqrt((accuracy_df['proj_error'] ** 2).mean())
                    st.metric("RMSE", f"{rmse:.2f} pts")
                with col3:
                    mape = accuracy_df['proj_error_pct'].abs().mean()
                    st.metric("Mean Absolute % Error", f"{mape:.1f}%")
                
                # Projection accuracy scatter
                fig = px.scatter(
                    accuracy_df,
                    x=proj_col,
                    y='FPTS',
                    hover_data=['name'],
                    title="Projected vs Actual Fantasy Points",
                    labels={proj_col: 'Projected Points', 'FPTS': 'Actual Points'}
                )
                # Add perfect projection line
                max_pts = max(accuracy_df[proj_col].max(), accuracy_df['FPTS'].max())
                fig.add_trace(go.Scatter(
                    x=[0, max_pts], y=[0, max_pts],
                    mode='lines', line=dict(dash='dash', color='gray'),
                    name='Perfect Projection'
                ))
                st.plotly_chart(fig, use_container_width=True)
                
                # Show biggest misses
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📈 Biggest Positive Surprises")
                    over_performers = accuracy_df.nlargest(10, 'proj_error')
                    st.dataframe(
                        over_performers[['name', proj_col, 'FPTS', 'proj_error', 'Own%']],
                        use_container_width=True
                    )
                with col2:
                    st.subheader("📉 Biggest Busts")
                    under_performers = accuracy_df.nsmallest(10, 'proj_error')
                    st.dataframe(
                        under_performers[['name', proj_col, 'FPTS', 'proj_error', 'Own%']],
                        use_container_width=True
                    )
            
            # Boom% calibration
            if boom_col and boom_col in accuracy_df.columns and ceil_col and ceil_col in accuracy_df.columns:
                st.subheader("🎯 Boom Probability Calibration")
                
                # Define boom threshold (e.g., hit ceiling)
                accuracy_df['hit_boom'] = accuracy_df['FPTS'] >= accuracy_df[ceil_col]
                
                # Bin boom probabilities
                accuracy_df['boom_bin'] = pd.cut(accuracy_df[boom_col], bins=[0, 10, 20, 30, 40, 50, 100])
                
                calibration = accuracy_df.groupby('boom_bin').agg({
                    'hit_boom': ['mean', 'count'],
                    boom_col: 'mean'
                }).round(3)
                
                st.write("**Calibration Table:** For each boom% range, what % actually boomed?")
                st.dataframe(calibration, use_container_width=True)
        else:
            st.warning("Could not match player names between boom/bust file and results")
    
    # --------------------------------------------------------
    # TAB 6: ROI Tracker
    # --------------------------------------------------------
    with tab6:
        st.header("💰 ROI & Profit Tracking")
        
        st.markdown("### Contest Settings")
        col1, col2, col3 = st.columns(3)
        with col1:
            entry_fee = st.number_input("Entry Fee ($)", value=20, min_value=1)
        with col2:
            total_entries = st.number_input("Your Total Entries", value=len(my_entries_df), min_value=1)
        with col3:
            prize_pool = st.number_input("Total Prize Pool ($)", value=20000, min_value=0)
        
        total_invested = entry_fee * total_entries
        
        # Define payout structure (example for $20 entry)
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
        if 'Rank' in my_entries_df.columns or find_column(my_entries_df, ['rank', 'finish']):
            rank_col = 'Rank' if 'Rank' in my_entries_df.columns else find_column(my_entries_df, ['rank', 'finish'])
            
            my_entries_df['Prize'] = my_entries_df[rank_col].map(payouts).fillna(0)
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
                display_cols = [rank_col, 'Prize']
                if points_col and points_col in cashing.columns:
                    display_cols.append(points_col)
                if my_lineup_col and my_lineup_col in cashing.columns:
                    display_cols.append(my_lineup_col)
                st.dataframe(cashing[display_cols], use_container_width=True)
            else:
                st.info("No lineups cashed in this contest")
        else:
            st.warning("Rank column not found - cannot calculate ROI")
    
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
    st.info("👆 Upload all 4 required files to begin analysis")
    
    st.markdown("""
    ### Required Files:
    
    1. **Player Ownership & FPTS** - DraftKings contest results export
       - Columns: Player name, Own%, FPTS, Salary, Position
       
    2. **Contest Top 0.1%** - Top finishing lineups
       - Columns: Rank, Points, Lineup (space-separated player names)
       
    3. **My Entries** - Your contest lineups
       - Columns: Rank, Points, Lineup (space-separated player names)
       
    4. **Boom/Bust Projections** - Your pre-contest projections
       - Columns: name, Boom%, proj_adj, ceiling_adj, stddev_adj, Own%, team, opp
    """)
