import streamlit as st
import pandas as pd
import numpy as np

# st.set_page_config(page_title="Ownership Adjuster - Thanksgiving Slate", layout="wide")

def run():
    """Main entry point for this tool"""
    st.title("🦃 Ownership Percentage Adjuster - Thanksgiving Slate")

    st.markdown("""
    Adjust ownership projections to match DraftKings roster construction requirements.
    Upload your Players.csv and this tool will normalize ownership percentages.
    """)

    # Upload file
    uploaded_file = st.file_uploader("Upload Players.csv", type=['csv'])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
    
        st.success(f"✅ Loaded {len(df)} players")
    
        # Display current ownership
        st.subheader("📊 Current Ownership Summary")
    
        position_summary = df.groupby('Position')['dk_ownership'].agg(['sum', 'count']).round(4)
        position_summary['avg'] = (position_summary['sum'] / position_summary['count']).round(4)
        position_summary['sum_pct'] = (position_summary['sum'] * 100).round(2)
    
        st.dataframe(position_summary)
    
        total_ownership = df['dk_ownership'].sum()
        st.metric("Total Ownership", f"{total_ownership*100:.2f}%", 
                 help="Should be 9.0 (900%) for a full DK lineup")
    
        # Adjustment settings
        st.markdown("---")
        st.subheader("⚙️ Ownership Constraints")
    
        col1, col2 = st.columns(2)
    
        with col1:
            st.markdown("**DraftKings Roster (9 positions):**")
            st.write("- 1 QB")
            st.write("- 2 RB")
            st.write("- 3 WR")
            st.write("- 1 TE")
            st.write("- 1 FLEX (RB/WR/TE)")
            st.write("- 1 DST")
            st.write("")
            st.markdown("**Required Ownership Totals:**")
            st.write("- DST: 100% (1 player)")
            st.write("- QB: 100% (1 player)")
            st.write("- TE: 100-200% (1-2 players via FLEX)")
            st.write("- RB: 200-300% (2-3 players via FLEX)")
            st.write("- WR: 300-400% (3-4 players via FLEX)")
            st.write("- **Total: 900% (fixed)**")
    
        with col2:
            st.markdown("**Current Totals:**")
            for pos in ['DST', 'QB', 'TE', 'RB', 'WR']:
                pos_total = df[df['Position'] == pos]['dk_ownership'].sum() * 100
                st.write(f"- {pos}: {pos_total:.1f}%")
            st.write("")
            st.metric("Total", f"{total_ownership*100:.1f}%", 
                     delta=f"{(total_ownership - 9.0)*100:+.1f}%" if total_ownership != 9.0 else "✓",
                     help="Must equal 900% (9.0)")
    
        # FLEX distribution
        st.markdown("---")
        st.subheader("🎯 FLEX Position Distribution")
    
        st.markdown("""
        The FLEX position can be filled by RB, WR, or TE. Adjust the sliders to set how the FLEX position
        is distributed across these positions. This determines the target totals for each position.
        """)
    
        col1, col2, col3 = st.columns(3)
    
        with col1:
            flex_rb = st.slider("FLEX → RB %", 0, 100, 50, 5, 
                               help="Percentage of FLEX filled by RBs")
        with col2:
            flex_wr = st.slider("FLEX → WR %", 0, 100, 50, 5,
                               help="Percentage of FLEX filled by WRs")
        with col3:
            flex_te = st.slider("FLEX → TE %", 0, 100, 0, 5,
                               help="Percentage of FLEX filled by TEs")
    
        flex_total = flex_rb + flex_wr + flex_te
    
        if flex_total != 100:
            st.error(f"⚠️ FLEX distribution must equal 100% (currently {flex_total}%)")
            st.stop()
    
        # Calculate targets based on FLEX distribution
        targets = {
            'DST': 1.0,
            'QB': 1.0,
            'TE': 1.0 + (flex_te / 100),
            'RB': 2.0 + (flex_rb / 100),
            'WR': 3.0 + (flex_wr / 100)
        }
    
        st.success(f"✅ Target totals: DST=100%, QB=100%, TE={targets['TE']*100:.0f}%, RB={targets['RB']*100:.0f}%, WR={targets['WR']*100:.0f}% = 900%")
    
        # Adjustment method
        st.markdown("---")
        st.subheader("🔧 Adjustment Method")
    
        method = st.radio(
            "Choose adjustment method:",
            ["Thanksgiving Model (Full)", "Projection-Based (Simple)", "Proportional Scaling"],
            help="Thanksgiving Model uses the complete algorithm with position ranks, multipliers, and soft caps. Simple methods are faster alternatives."
        )
    
        # Advanced settings for Thanksgiving Model
        if method == "Thanksgiving Model (Full)":
            with st.expander("⚙️ Advanced Settings", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    intensity_factor = st.slider("Intensity Factor", 1.0, 5.0, 3.0, 0.1,
                                                help="Higher = more concentration on top players")
                    st.markdown("**Position Multipliers:**")
                    st.write("Top-ranked players get boosted ownership")
                with col2:
                    st.markdown("**Soft Caps (%):**")
                    cap_qb = st.number_input("QB Max", 50, 100, 70, 5)
                    cap_rb = st.number_input("RB Max", 50, 100, 65, 5)
                    cap_wr = st.number_input("WR Max", 50, 100, 60, 5)
                    cap_te = st.number_input("TE Max", 40, 100, 55, 5)
                    cap_dst = st.number_input("DST Max", 40, 100, 50, 5)
    
        if st.button("🚀 Adjust Ownership", type="primary"):
        
            df_adjusted = df.copy()
        
            if method == "Thanksgiving Model (Full)":
                st.info("Running full Thanksgiving ownership model...")
            
                # Step 1: Filter low projections
                df_adjusted['eligible'] = df_adjusted['median_proj'] >= 1.0
            
                # Step 2: Compute/verify value
                df_adjusted['value'] = df_adjusted['median_proj'] / (df_adjusted['Salary'] / 1000)
            
                # Step 3: Percentile ranks (only for eligible players)
                eligible_mask = df_adjusted['eligible']
            
                df_adjusted['proj_pct_rank'] = 0.0
                df_adjusted['value_pct_rank'] = 0.0
            
                if eligible_mask.sum() > 1:
                    # Percentile rank: (rank - 1) / (N - 1)
                    df_adjusted.loc[eligible_mask, 'proj_pct_rank'] = \
                        df_adjusted.loc[eligible_mask, 'median_proj'].rank(pct=True)
                    df_adjusted.loc[eligible_mask, 'value_pct_rank'] = \
                        df_adjusted.loc[eligible_mask, 'value'].rank(pct=True)
            
                # Step 4: Base popularity
                df_adjusted['base_popularity'] = \
                    0.6 * df_adjusted['proj_pct_rank'] + 0.4 * df_adjusted['value_pct_rank']
            
                # Step 5: Position rank
                df_adjusted['pos_rank'] = df_adjusted.groupby('Position')['base_popularity'] \
                    .rank(method='first', ascending=False).astype(int)
            
                # Step 6: Thanksgiving position multipliers
                def get_tg_multiplier(row):
                    if not row['eligible']:
                        return 0.0
                    pos = row['Position']
                    rank = row['pos_rank']
                
                    if pos == 'QB':
                        if rank == 1: return 1.35
                        elif rank == 2: return 1.20
                        elif rank == 3: return 1.05
                        else: return 1.00
                    elif pos in ['RB', 'WR']:
                        if rank == 1: return 1.40
                        elif rank == 2: return 1.25
                        elif rank == 3: return 1.10
                        elif rank <= 5: return 1.03
                        else: return 1.00
                    elif pos == 'TE':
                        if rank == 1: return 1.35
                        elif rank == 2: return 1.18
                        elif rank == 3: return 1.05
                        else: return 1.00
                    elif pos == 'DST':
                        if rank == 1: return 1.30
                        elif rank == 2: return 1.15
                        elif rank == 3: return 1.05
                        else: return 1.00
                    return 1.00
            
                df_adjusted['tg_pos_mult'] = df_adjusted.apply(get_tg_multiplier, axis=1)
                df_adjusted['adj_popularity'] = df_adjusted['base_popularity'] * df_adjusted['tg_pos_mult']
            
                # Step 7: Raw ownership weights (exponential curve)
                df_adjusted['raw_own_weight'] = np.exp(intensity_factor * df_adjusted['adj_popularity'])
                df_adjusted.loc[~eligible_mask, 'raw_own_weight'] = 0.0
            
                # Step 8: Normalize each position to its target (from FLEX distribution)
                df_adjusted['init_tg_own'] = 0.0
            
                for pos, target in targets.items():
                    pos_mask = df_adjusted['Position'] == pos
                    pos_weight_total = df_adjusted.loc[pos_mask, 'raw_own_weight'].sum()
                
                    if pos_weight_total > 0:
                        # Normalize this position's weights to hit the target total
                        df_adjusted.loc[pos_mask, 'init_tg_own'] = \
                            (df_adjusted.loc[pos_mask, 'raw_own_weight'] / pos_weight_total) * target
            
                # Step 9: Apply soft caps by position (individual player caps)
                caps = {
                    'QB': cap_qb / 100,
                    'RB': cap_rb / 100,
                    'WR': cap_wr / 100,
                    'TE': cap_te / 100,
                    'DST': cap_dst / 100
                }
            
                df_adjusted['capped_tg_own'] = df_adjusted['init_tg_own']
                for pos, cap in caps.items():
                    pos_mask = df_adjusted['Position'] == pos
                    # Cap individual players, but then need to redistribute
                    over_cap = df_adjusted.loc[pos_mask & (df_adjusted['capped_tg_own'] > cap)]
                    if len(over_cap) > 0:
                        # Set capped players to cap
                        df_adjusted.loc[pos_mask & (df_adjusted['capped_tg_own'] > cap), 'capped_tg_own'] = cap
                    
                        # Calculate excess that was removed
                        excess = df_adjusted.loc[pos_mask, 'init_tg_own'].sum() - df_adjusted.loc[pos_mask, 'capped_tg_own'].sum()
                    
                        # Redistribute excess proportionally to uncapped players in same position
                        uncapped_mask = pos_mask & (df_adjusted['init_tg_own'] <= cap) & (df_adjusted['init_tg_own'] > 0)
                        uncapped_total = df_adjusted.loc[uncapped_mask, 'capped_tg_own'].sum()
                    
                        if uncapped_total > 0 and excess > 0:
                            df_adjusted.loc[uncapped_mask, 'capped_tg_own'] += \
                                (df_adjusted.loc[uncapped_mask, 'capped_tg_own'] / uncapped_total) * excess
            
                # Final values
                df_adjusted['thanksgiving_proj_own'] = df_adjusted['capped_tg_own']
            
                # Update dk_ownership with final values
                df_adjusted['dk_ownership'] = df_adjusted['thanksgiving_proj_own']
            
                # Show intermediate metrics
                st.markdown("**Position Ranks & Multipliers:**")
                rank_display = df_adjusted[['Player', 'Position', 'pos_rank', 'tg_pos_mult', 'thanksgiving_proj_own']].sort_values('thanksgiving_proj_own', ascending=False).head(15)
                rank_display['thanksgiving_proj_own'] = (rank_display['thanksgiving_proj_own'] * 100).round(2)
                st.dataframe(rank_display.rename(columns={'thanksgiving_proj_own': 'Own %'}))
            
            elif method == "Projection-Based (Simple)":
                # Calculate ownership based on median projection and salary
                st.info("Calculating ownership from median projections and salary (value-based)...")
            
                # Calculate value metric: median_proj / (Salary / 1000)
                df_adjusted['value'] = df_adjusted['median_proj'] / (df_adjusted['Salary'] / 1000)
            
                for pos, target in targets.items():
                    pos_mask = df_adjusted['Position'] == pos
                    pos_df = df_adjusted[pos_mask].copy()
                
                    if len(pos_df) > 0:
                        # Normalize value to 0-1 range within position
                        min_val = pos_df['value'].min()
                        max_val = pos_df['value'].max()
                        pos_df['value_norm'] = (pos_df['value'] - min_val) / (max_val - min_val) if max_val > min_val else 0.5
                    
                        # Apply exponential curve with higher exponent for more concentration
                        # Using power of 3 creates steeper ownership curve
                        pos_df['raw_ownership'] = np.power(pos_df['value_norm'], 3)
                    
                        # Ensure minimum 1% ownership for anyone in player pool
                        pos_df['raw_ownership'] = np.maximum(pos_df['raw_ownership'], 0.01)
                    
                        # Normalize to target total
                        total_raw = pos_df['raw_ownership'].sum()
                        pos_df['dk_ownership'] = (pos_df['raw_ownership'] / total_raw) * target
                    
                        # Update main dataframe
                        df_adjusted.loc[pos_mask, 'dk_ownership'] = pos_df['dk_ownership'].values
                    
                        st.write(f"**{pos}**: Ownership calculated from value → {target*100:.0f}%")
            
                # Drop helper columns
                df_adjusted = df_adjusted.drop(['value', 'value_norm'], axis=1, errors='ignore')
            
            else:  # Proportional Scaling
                st.info("Scaling each position to target totals...")
            
                for pos, target in targets.items():
                    pos_players = df_adjusted['Position'] == pos
                    current_total = df_adjusted.loc[pos_players, 'dk_ownership'].sum()
                
                    if current_total > 0:
                        scale_factor = target / current_total
                        df_adjusted.loc[pos_players, 'dk_ownership'] *= scale_factor
                    
                        st.write(f"**{pos}**: {current_total*100:.1f}% → {target*100:.0f}% (factor: {scale_factor:.3f})")
        
            # Final validation
            st.markdown("---")
            st.subheader("✅ Adjusted Ownership Summary")
        
            position_summary_adj = df_adjusted.groupby('Position')['dk_ownership'].agg(['sum', 'count']).round(4)
            position_summary_adj['sum_pct'] = (position_summary_adj['sum'] * 100).round(2)
        
            col1, col2 = st.columns(2)
        
            with col1:
                st.dataframe(position_summary_adj)
        
            with col2:
                total_ownership_adj = df_adjusted['dk_ownership'].sum()
                st.metric("Total Ownership (Adjusted)", f"{total_ownership_adj*100:.2f}%",
                         delta=f"{(total_ownership_adj - total_ownership)*100:+.2f}%")
            
                if abs(total_ownership_adj - 9.0) < 0.01:
                    st.success("✅ Total ownership equals 900% (9.0)")
                else:
                    st.error(f"❌ Total ownership is {total_ownership_adj*100:.1f}% (must be exactly 900%)")
                    st.info("This shouldn't happen - please report this issue.")
        
            # Show adjusted players
            st.markdown("---")
            st.subheader("📋 Adjusted Player Ownership")
        
            # Create comparison dataframe
            comparison_df = df[['Player', 'Position', 'Team', 'Salary', 'dk_ownership']].copy()
            comparison_df['dk_ownership_original'] = comparison_df['dk_ownership']
            comparison_df['dk_ownership_adjusted'] = df_adjusted['dk_ownership']
            comparison_df['change'] = comparison_df['dk_ownership_adjusted'] - comparison_df['dk_ownership_original']
        
            # Format for display
            display_df = comparison_df.copy()
            display_df['Original %'] = (display_df['dk_ownership_original'] * 100).round(2)
            display_df['Adjusted %'] = (display_df['dk_ownership_adjusted'] * 100).round(2)
            display_df['Change %'] = (display_df['change'] * 100).round(2)
        
            st.dataframe(
                display_df[['Player', 'Position', 'Team', 'Salary', 'Original %', 'Adjusted %', 'Change %']].style.format({
                    'Salary': '${:,.0f}',
                    'Original %': '{:.2f}%',
                    'Adjusted %': '{:.2f}%',
                    'Change %': '{:+.2f}%'
                }),
                height=600,
                use_container_width=True
            )
        
            # Download adjusted file
            st.markdown("---")
        
            # Prepare output dataframe (replace dk_ownership column)
            df_output = df.copy()
            df_output['dk_ownership'] = df_adjusted['dk_ownership']
        
            csv = df_output.to_csv(index=False)
        
            st.download_button(
                label="📥 Download Adjusted Players.csv",
                data=csv,
                file_name="Players_adjusted.csv",
                mime="text/csv",
                type="primary"
            )
        
            st.success("✅ Ownership percentages adjusted! Download the file and use it in your optimizer.")

    else:
        st.info("👈 Upload your Players.csv file to begin")
    
        st.markdown("""
        ### How It Works:
    
        1. **Upload** your Players.csv with projections and salary data
        2. **Review** current ownership totals by position
        3. **Set FLEX distribution** - how the FLEX spot is filled (RB/WR/TE split)
        4. **Choose** adjustment method:
           - **Thanksgiving Model (Full)**: Complete algorithm with percentile ranks, position multipliers, exponential weighting, and soft caps
           - **Projection-Based (Simple)**: Quick value-based calculation
           - **Proportional Scaling**: Scales current ownership to match targets
        5. **Download** adjusted file with normalized ownership
    
        ### DraftKings Roster (9 positions):
        - 1 QB (100%)
        - 2 RB (200%)
        - 3 WR (300%)
        - 1 TE (100%)
        - 1 FLEX (100% distributed across RB/WR/TE based on your settings)
        - 1 DST (100%)
        - **Total: 900% ownership (fixed constraint)**
    
        ### Why This Matters:
        Ownership projections must sum to exactly 900% because every DK lineup fills 9 positions.
        The FLEX distribution determines how that 9th position is split across RB/WR/TE.
        """)


# Standalone execution
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    run()
