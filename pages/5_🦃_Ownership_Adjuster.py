"""
Ownership Adjuster Tool Page  
Adjust ownership projections to match DK roster construction
"""

import streamlit as st
import pandas as pd
import numpy as np
from components.tables import display_styled_table, display_download_button
from components.layouts import create_metric_card, create_info_box
from utils.constants import ROSTER_CONSTRUCTION, SALARY_CAP

st.title("🦃 Ownership Percentage Adjuster")
st.caption("Adjust ownership projections to match DraftKings roster construction requirements")

st.markdown("""
Upload your Players.csv and this tool will normalize ownership percentages to match DK lineup construction (900% total).
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
    
    col1, col2, col3 = st.columns(3)
    with col1:
        create_metric_card("Total Ownership", f"{total_ownership*100:.2f}%", 
                          f"{(total_ownership - 9.0)*100:+.1f}%" if total_ownership != 9.0 else "✓")
    with col2:
        create_metric_card("Target", "900%", "9 positions")
    with col3:
        deviation = abs(total_ownership - 9.0) * 100
        create_metric_card("Deviation", f"{deviation:.1f}%", 
                          "✅ Within range" if deviation < 5 else "⚠️ Adjustment needed")
    
    # Roster construction info
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
        if abs(total_ownership - 9.0) < 0.05:
            create_info_box("✅ Ownership totals are balanced!", "success")
        else:
            create_info_box(f"⚠️ Adjustment needed: Current total is {total_ownership*100:.1f}%", "warning")
    
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
        'WR': 3.0 + (flex_wr / 100),
    }
    
    # Apply adjustments
    st.markdown("---")
    
    if st.button("🔧 Adjust Ownership", type="primary"):
        df_adjusted = df.copy()
        
        # Normalize each position to target
        for pos, target in targets.items():
            pos_mask = df_adjusted['Position'] == pos
            current_sum = df_adjusted.loc[pos_mask, 'dk_ownership'].sum()
            
            if current_sum > 0:
                adjustment_factor = target / current_sum
                df_adjusted.loc[pos_mask, 'dk_ownership'] = df_adjusted.loc[pos_mask, 'dk_ownership'] * adjustment_factor
        
        # Verify total
        new_total = df_adjusted['dk_ownership'].sum()
        
        st.success(f"✅ **Adjustment Complete!** New total: {new_total*100:.2f}% (target: 900%)")
        
        # Show before/after comparison
        st.subheader("📊 Before vs After")
        
        comparison_data = []
        for pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
            old_total = df[df['Position'] == pos]['dk_ownership'].sum() * 100
            new_total_pos = df_adjusted[df_adjusted['Position'] == pos]['dk_ownership'].sum() * 100
            target_pct = targets.get(pos, 1.0) * 100
            
            comparison_data.append({
                'Position': pos,
                'Before %': f"{old_total:.1f}%",
                'After %': f"{new_total_pos:.1f}%",
                'Target %': f"{target_pct:.1f}%",
                'Delta': f"{new_total_pos - old_total:+.1f}%"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, hide_index=True)
        
        # Display adjusted players table
        st.subheader("📋 Adjusted Players")
        
        display_cols = ['Name', 'Position', 'Salary', 'dk_ownership']
        display_df = df_adjusted[display_cols].copy()
        display_df['dk_ownership'] = (display_df['dk_ownership'] * 100).round(2)
        display_df = display_df.rename(columns={'dk_ownership': 'Ownership %'})
        display_df = display_df.sort_values(['Position', 'Ownership %'], ascending=[True, False])
        
        st.dataframe(display_df, hide_index=True)
        
        # Download button
        csv_data = df_adjusted.to_csv(index=False)
        display_download_button(
            data=csv_data,
            filename="players_adjusted_ownership.csv",
            button_text="📥 Download Adjusted Players CSV"
        )

else:
    create_info_box("👆 Upload a Players.csv file to begin", "info")
