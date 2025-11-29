import streamlit as st
import pandas as pd
import numpy as np
import math
import itertools

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
    players = pd.read_csv(r"C:\Users\schne\Documents\DFS\2025\Dashboard\Players.csv")
    matchups = pd.read_csv(r"C:\Users\schne\Documents\DFS\2025\Dashboard\Matchup.csv")
    team_offense = pd.read_csv(r"C:\Users\schne\Documents\DFS\2025\Dashboard\Team_Plays_Offense.csv")
    team_defense = pd.read_csv(r"C:\Users\schne\Documents\DFS\2025\Dashboard\Team_Plays_Defense.csv")
    def_strength = pd.read_csv(r"C:\Users\schne\Documents\DFS\2025\Dashboard\Weighted Z-Score Allowed.csv")

    # Rename for consistency
    players = players.rename(
        columns={
            "Player": "name",
            "Position": "position",
            "Team": "team",
            "Salary": "salary",
            "median_proj": "proj",
            "ceiling_proj": "ceiling_ows",
            "Var DK": "var_dk",
            "dk_ownership": "dk_ownership",
            "Max DK": "max_dk",
            "Avg DK": "avg_dk",
            "4x Hits": "hits_4x",
        }
    )

    # Convert numeric cols
    numeric_cols = ["proj", "ceiling_ows", "salary", "var_dk", "dk_ownership", "max_dk", "avg_dk", "hits_4x"]
    for col in numeric_cols:
        players[col] = pd.to_numeric(players[col], errors="coerce")

    # Only drop rows missing essential fields (proj, ceiling, salary)
    players = players.dropna(subset=["proj", "ceiling_ows", "salary"])
    
    # Fill missing variance/ownership with defaults so players aren't excluded
    players["var_dk"] = players["var_dk"].fillna(players["proj"] * 0.5)  # Default variance = 50% of projection
    players["dk_ownership"] = players["dk_ownership"].fillna(0.01)  # Default 1% ownership
    players["hits_4x"] = players["hits_4x"].fillna(0)  # Default 0 historical booms
    players["max_dk"] = players["max_dk"].fillna(players["ceiling_ows"])  # Default max = ceiling
    players["avg_dk"] = players["avg_dk"].fillna(players["proj"])  # Default avg = projection

    # Std dev
    players["stddev"] = np.sqrt(players["var_dk"])
    
    # Get opponent for each player and merge defensive strength
    # First get opponent from matchup dict
    matchup_dict_temp = matchups.set_index("Init")["Opp"].to_dict()
    players["opponent"] = players["team"].map(matchup_dict_temp)
    
    # Merge defensive strength z-score
    players = players.merge(
        def_strength,
        left_on=["opponent", "position"],
        right_on=["Opp", "Position"],
        how="left"
    )
    players["def_z_score"] = players["Weighted Z Allowed"].fillna(0)  # Default to 0 if no matchup data
    
    # Adjust projection and stddev based on defensive matchup
    # Positive z-score = weaker defense (good for offense) → boost projection
    # Negative z-score = stronger defense (bad for offense) → lower projection
    # Scale factor: 1 std dev in defense strength = ~5-10% projection adjustment
    players["matchup_factor"] = 1 + (players["def_z_score"] * 0.075)  # 7.5% per std dev
    players["proj_adj"] = players["proj"] * players["matchup_factor"]
    players["ceiling_adj"] = players["ceiling_ows"] * players["matchup_factor"]
    
    # Also adjust variance slightly (better matchups = slightly higher variance/upside)
    players["stddev_adj"] = players["stddev"] * (1 + players["def_z_score"] * 0.05)

    # Percentile Z-Tables (using adjusted values)
    z_75 = 0.674
    players["floor_25"] = (players["proj_adj"] - z_75 * players["stddev_adj"]).clip(lower=0)
    players["ceil_75"] = players["proj_adj"] + z_75 * players["stddev_adj"]

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

    # Compute boom/bust for each player (using matchup-adjusted values)
    for _, row in players.iterrows():
        pos = row["position"]
        sal = row["salary"]
        sal_k = sal / 1000.0
        mean = row["proj_adj"]  # Use adjusted projection
        std = row["stddev_adj"]   # Use adjusted stddev

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

    # Opponent dictionary
    matchup_dict = matchups.set_index("Init")["Opp"].to_dict()
    matchup_expanded = matchups.set_index("Init").to_dict(orient="index")
    
    # Team pace/plays dictionaries
    team_offense_dict = team_offense.set_index("Team").to_dict(orient="index")
    team_defense_dict = team_defense.set_index("Opp").to_dict(orient="index")
    
    return players, matchups, matchup_dict, matchup_expanded, team_offense_dict, team_defense_dict


df, matchups, matchup_dict, matchup_expanded, team_offense_dict, team_defense_dict = load_data()


# --------------------------------------------------------
# Streamlit Page Config
# --------------------------------------------------------
st.set_page_config(page_title="NFL Top Stacks + Boom/Bust Tool", layout="wide")

st.title("🏈 NFL Top Stacks + Boom/Bust Tool")
st.caption("Player-level Boom/Bust model + matchup-aware stack explorer")

# Sidebar filters
st.sidebar.title("⚙️ Configuration")

# Player Filters
with st.sidebar.expander("🎯 Player Filters", expanded=True):
    st.caption("Filter the player pool before generating stacks")
    min_proj = st.slider("Min Projection", 0.0, 40.0, 5.0, 0.5, key="min_proj")
    min_ceiling = st.slider("Min Ceiling", 0.0, 60.0, 15.0, 0.5, key="min_ceiling")
    min_4x_hits = st.slider("Min 4x Hits (Historical Booms)", 0, 10, 0, 1, key="min_4x")

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

df_filtered = df[(df["dk"] >= min_proj) & (df["dk_ceiling"] >= min_ceiling) & (df["hits_4x"] >= min_4x_hits)]


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

        team_combos = list(itertools.combinations(team_skill.to_dict("records"), team_size))

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

        for combo in team_combos:

            stack_players = [qb.to_dict()] + list(combo)
            
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
                # Var(X+Y) = Var(X) + Var(Y) + 2*Cov(X,Y)
                # Cov(X,Y) = rho * std(X) * std(Y)
                
                # Start with sum of individual variances
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

                # Compute relative matchup metrics
                def rel_metric(off, def_):
                    try:
                        return float(team_matchup.get(off, 0)) - float(opp_matchup.get(def_, 0))
                    except Exception:
                        return None

                epa_adv = rel_metric("Init_EPA_Play", "Opp_EPA_Play_Allowed")
                ypp_adv = rel_metric("Init_Yards Per Play", "Opp_Yards Per Play Allowed")
                ptd_adv = rel_metric("Init_Points Per Drive", "Opp_Points Per Drive Allowed")
                exp_adv = rel_metric("Init_Explosive Play Rate", "Opp_Explosive Play Rate Allowed")
                dcr_adv = rel_metric("Init_Down Conversion Rate", "Opp_Down Conversion Rate Allowed")
                
                # Game Environment Score (pace + matchup quality)
                game_env_score = None
                try:
                    team_off = team_offense_dict.get(team, {})
                    opp_def = team_defense_dict.get(opp, {})
                    opp_off = team_offense_dict.get(opp, {})
                    
                    # Avg plays (higher = more opportunities)
                    team_plays = float(team_off.get("Avg Plays", 0))
                    opp_plays = float(opp_off.get("Avg Plays", 0))
                    game_plays = (team_plays + opp_plays) / 2
                    
                    # Pass volume (higher for pass-heavy stacks)
                    team_pass_att = float(team_off.get("Avg Pass Att", 0))
                    
                    # ITT from matchup
                    team_itt = float(team_matchup.get("ITT", 0))
                    
                    # Normalize and weight components (0-100 scale)
                    # Game plays: 48-62 range → 0-100
                    plays_score = ((game_plays - 48) / (62 - 48)) * 100
                    # Pass attempts: 26-40 range → 0-100
                    pass_score = ((team_pass_att - 26) / (40 - 26)) * 100
                    # ITT: 13-32 range → 0-100
                    itt_score = ((team_itt - 13) / (32 - 13)) * 100
                    # EPA advantage: -0.2 to 0.2 range → 0-100
                    epa_score = ((epa_adv or 0) + 0.2) / 0.4 * 100 if epa_adv is not None else 50
                    
                    # Weighted composite: plays(30%) + pass(25%) + ITT(25%) + EPA(20%)
                    game_env_score = (
                        plays_score * 0.30 +
                        pass_score * 0.25 +
                        itt_score * 0.25 +
                        epa_score * 0.20
                    )
                    game_env_score = max(0, min(100, game_env_score))  # Clamp to 0-100
                except Exception:
                    game_env_score = None

                # Calculate stack value (projection per $1K salary)
                stack_value = (total_proj / (total_salary / 1000)) if total_salary > 0 else 0

                results.append({
                    "QB": qb["name"],
                    "Team": team,
                    "Opp": opp,
                    "Players": ", ".join([p["name"] for p in stack_all]),
                    "Total_Proj": round(total_proj, 2),
                    "Total_Ceiling_Adj": round(total_ceiling_adj, 2),
                    "Ceiling_vs_Proj": round(total_ceiling - total_proj, 2),
                    "Ceil_Adj_vs_Proj": round(total_ceiling_adj - total_proj, 2),
                    "Stack_Value": round(stack_value, 2),
                    "Total_Salary": int(total_salary),
                    "Total_Own": round(total_own, 4),
                    "Total_Own%": round(total_own * 100, 1),
                    "Boom_Target": round(stack_boom_target, 1),  # Display actual boom threshold
                    "Stack_Boom%": round(stack_boom_prob * 100, 1),
                    "Stack_Leverage": round(stack_leverage, 1),
                    "Game_Env_Score": round(game_env_score, 1) if game_env_score is not None else None,
                    "EPA_Adv": epa_adv,
                    "YPP_Adv": ypp_adv,
                    "PTD_Adv": ptd_adv,
                    "EXP_Adv": exp_adv,
                    "DCR_Adv": dcr_adv,
                })

    df_results = pd.DataFrame(results)
    
    # Limit to top 4 stacks per team (by Stack_Leverage)
    if not df_results.empty:
        df_results = (
            df_results
            .sort_values("Stack_Leverage", ascending=False)
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
    
    col1, col2 = st.columns([1, 3])
    with col1:
        positions = sorted(df_filtered["position"].unique())
        pos_filter = st.selectbox("Position:", ["All"] + positions)
    with col2:
        st.info("💡 **Green** = Good for GPPs | **Yellow** = Average | **Red** = Avoid or fade")

    df_pos = df_filtered if pos_filter == "All" else df_filtered[df_filtered["position"] == pos_filter]

    display_df = df_pos.copy()
    
    # Reset index to show row numbers starting from 1
    display_df = display_df.reset_index(drop=True)
    display_df.index = display_df.index + 1
    display_df.index.name = "#"
    
    display_df["Boom%"] = (display_df["boom_prob"] * 100).round(1)
    display_df["Bust%"] = (display_df["bust_prob"] * 100).round(1)
    display_df["Own%"] = (display_df["dk_ownership"] * 100).round(1)
    display_df["Lev (Boom-Own)%"] = (display_df["leverage_boom"] * 100).round(1)
    display_df["Def Z"] = display_df["def_z_score"].round(2)
    display_df["Salary"] = display_df["salary"]  # Keep raw value for color-coding
    display_df["Pts/$K"] = (display_df["ceiling_adj"] / (display_df["salary"] / 1000)).round(2)

    cols = [
        "name", "team", "opponent", "position", "Salary", "Pts/$K",
        "proj_adj", "stddev_adj", "ceiling_adj", "max_dk", "avg_dk", "floor_25", "ceil_75",
        "Def Z", "Boom%", "Bust%", "Own%", "Lev (Boom-Own)%", "hits_4x"
    ]

    # --------------------------------------------------------
    # Dynamic RAG scaling based on filtered dataset (display_df)
    # --------------------------------------------------------
    def rag_relative(df, col, reverse=False):
        """
        reverse=False → high = green (Boom%, Leverage)
        reverse=True  → low = green (Bust%, Own%)
        """
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
    
    styled = (
        display_df[cols]
        .style
        .format("{:.1f}", subset=["proj_adj", "stddev_adj", "ceiling_adj", "max_dk", "avg_dk", "floor_25", "ceil_75"])
        .format("{:.2f}", subset=["Def Z", "Pts/$K"])
        .format("{:.1f}", subset=["Boom%", "Bust%", "Own%", "Lev (Boom-Own)%"])
        .format("{:.0f}", subset=["hits_4x"])
        .format("${:,.0f}", subset=["Salary"])  # Currency format for salary
        .map(rag_relative(display_df, "Pts/$K"), subset=["Pts/$K"])  # Higher value = better
        .map(rag_relative(display_df, "Salary", reverse=True), subset=["Salary"])  # Lower salary = better value
        .map(rag_relative(display_df, "ceiling_adj"), subset=["ceiling_adj"])  # Higher ceiling = better
        .map(rag_relative(display_df, "Def Z"), subset=["Def Z"])  # Positive = good matchup
        .map(rag_relative(display_df, "Boom%"), subset=["Boom%"])
        .map(rag_relative(display_df, "Bust%", reverse=True), subset=["Bust%"])
        .map(ownership_color, subset=["Own%"])  # Fixed thresholds for ownership
        .map(rag_relative(display_df, "Lev (Boom-Own)%"), subset=["Lev (Boom-Own)%"])
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
        with st.spinner("🔄 Generating stacks..."):
            stack_df = get_stack(df_filtered, matchup_dict, stack_option, stack_positions, bringback_positions)

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
                    - **Stack_Value**: Projection per $1K salary (value play identifier)
                    - **Boom_Target**: DK points threshold for boom (95th percentile, calibrated to 230+ winning lineups)
                    - **Stack_Boom%**: Probability stack exceeds boom threshold
                    - **Stack_Leverage**: Boom% minus Ownership% (positive = leverage)
                    - **Game_Env_Score**: 0-100 composite (pace + volume + ITT + EPA)
                    - **Total_Ceiling_Adj**: Matchup-adjusted ceiling sum
                    """)
                with col2:
                    st.markdown("""
                    **Matchup Metrics (Advantage = Team Offense vs Opp Defense):**
                    - **EPA_Adv**: Expected Points Added advantage
                    - **YPP_Adv**: Yards Per Play advantage
                    - **PTD_Adv**: Points Per Drive advantage
                    - **EXP/DCR_Adv**: Explosive Play / Down Conversion Rate
                    """)

            # Sorting
            if rank_metric == "Total_Salary (Asc)":
                stack_df = stack_df.sort_values("Total_Salary", ascending=True)
            elif rank_metric == "Total_Own (Asc)":
                stack_df = stack_df.sort_values("Total_Own", ascending=True)
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
                "Total_Proj", "Total_Ceiling_Adj", "Ceiling_vs_Proj", "Ceil_Adj_vs_Proj",
                "Stack_Value", "Total_Salary", "Total_Own%", "Boom_Target", "Stack_Boom%", "Stack_Leverage",
                "Game_Env_Score", "EPA_Adv", "YPP_Adv", "PTD_Adv", "EXP_Adv", "DCR_Adv"
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
            
            # Color function for Boom_Target
            def color_boom_target(row):
                styles = [''] * len(row)
                boom_idx = display_df.columns.get_loc("Boom_Target")
                if row["Boom_Target"] > row["Total_Ceiling_Adj"]:
                    styles[boom_idx] = 'background-color: #E74C3C; color: white;'
                else:
                    styles[boom_idx] = 'background-color: #2ECC71; color: black;'
                return styles
            
            # Apply styling
            styled_stacks = (
                display_df.style
                .format("{:.1f}", subset=["Total_Proj", "Total_Ceiling_Adj", "Ceiling_vs_Proj", "Ceil_Adj_vs_Proj",
                                           "Boom_Target", "Stack_Boom%", "Stack_Leverage", "Game_Env_Score"])
                .format("{:.2f}", subset=["Stack_Value", "EPA_Adv", "YPP_Adv", "PTD_Adv", "EXP_Adv", "DCR_Adv"])
                .format("{:.1f}", subset=["Total_Own%"])
                .format("${:,.0f}", subset=["Total_Salary"])
                .apply(color_boom_target, axis=1)
                .map(stack_rag(stack_df, "Stack_Value"), subset=["Stack_Value"])
                .map(stack_rag(stack_df, "Total_Ceiling_Adj"), subset=["Total_Ceiling_Adj"])
                .map(stack_rag(stack_df, "Ceil_Adj_vs_Proj"), subset=["Ceil_Adj_vs_Proj"])
                .map(stack_rag(stack_df, "Stack_Boom%"), subset=["Stack_Boom%"])
                .map(stack_rag(stack_df, "Stack_Leverage"), subset=["Stack_Leverage"])
                .map(stack_rag(stack_df, "Game_Env_Score"), subset=["Game_Env_Score"])
                .map(stack_rag(stack_df, "Total_Own%", reverse=True), subset=["Total_Own%"])
                .map(stack_rag(stack_df, "EPA_Adv"), subset=["EPA_Adv"])
                .map(stack_rag(stack_df, "Total_Salary", reverse=True), subset=["Total_Salary"])
            )

            st.dataframe(styled_stacks, width="stretch")

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
    st.caption("Team-level metrics comparison for all games on the slate")
    
    # Get list of teams that are actually on the main slate (from players data)
    main_slate_teams = set(df["team"].unique())
    
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
        
        # Get team offensive stats
        init_off = team_offense_dict.get(init_team, {})
        opp_off = team_offense_dict.get(opp_team, {})
        
        # Get team defensive stats
        init_def = team_defense_dict.get(init_team, {})
        opp_def = team_defense_dict.get(opp_team, {})
        
        # Get expanded matchup data
        init_matchup = matchup_expanded.get(init_team, {})
        opp_matchup = matchup_expanded.get(opp_team, {})
        
        # Calculate game environment score for each side
        try:
            init_plays = float(init_off.get("Avg Plays", 0))
            opp_plays = float(opp_off.get("Avg Plays", 0))
            game_pace = (init_plays + opp_plays) / 2
            
            init_pass_att = float(init_off.get("Avg Pass Att", 0))
            init_itt = float(init_matchup.get("ITT", 0))
            init_epa = float(init_matchup.get("Init_EPA_Play", 0))
            
            opp_pass_att = float(opp_off.get("Avg Pass Att", 0))
            opp_itt = float(opp_matchup.get("ITT", 0))
            opp_epa = float(opp_matchup.get("Init_EPA_Play", 0))
        except:
            game_pace = init_plays = opp_plays = 0
            init_pass_att = init_itt = init_epa = 0
            opp_pass_att = opp_itt = opp_epa = 0
        
        matchup_data.append({
            "Game": f"{init_team} @ {opp_team}",
            "Team": init_team,
            "Opp": opp_team,
            "Game_Pace": round(game_pace, 1),
            "Pass_Att": round(init_pass_att, 1),
            "ITT": round(init_itt, 1),
            "EPA": round(init_epa, 3),
            "YPP_Off": round(float(init_matchup.get("Init_Yards Per Play", 0)), 2),
            "PTD_Off": round(float(init_matchup.get("Init_Points Per Drive", 0)), 2),
            "DCR_Off": round(float(init_matchup.get("Init_Down Conversion Rate", 0)), 2),
            "YPP_Def_Allow": round(float(opp_matchup.get("Opp_Yards Per Play Allowed", 0)), 2),
            "PTD_Def_Allow": round(float(opp_matchup.get("Opp_Points Per Drive Allowed", 0)), 2),
        })
        
        # Add opponent side
        matchup_data.append({
            "Game": f"{init_team} @ {opp_team}",
            "Team": opp_team,
            "Opp": init_team,
            "Game_Pace": round(game_pace, 1),
            "Pass_Att": round(opp_pass_att, 1),
            "ITT": round(opp_itt, 1),
            "EPA": round(opp_epa, 3),
            "YPP_Off": round(float(opp_matchup.get("Init_Yards Per Play", 0)), 2),
            "PTD_Off": round(float(opp_matchup.get("Init_Points Per Drive", 0)), 2),
            "DCR_Off": round(float(opp_matchup.get("Init_Down Conversion Rate", 0)), 2),
            "YPP_Def_Allow": round(float(init_matchup.get("Opp_Yards Per Play Allowed", 0)), 2),
            "PTD_Def_Allow": round(float(init_matchup.get("Opp_Points Per Drive Allowed", 0)), 2),
        })
    
    matchup_df = pd.DataFrame(matchup_data)
    
    if not matchup_df.empty:
        # Sort by Game_Pace descending (highest pace games at top)
        matchup_df = matchup_df.sort_values("Game_Pace", ascending=False)
        
        # Reset index
        matchup_df = matchup_df.reset_index(drop=True)
        matchup_df.index = matchup_df.index + 1
        matchup_df.index.name = "#"
        
        # Metric legend
        with st.expander("📖 Metric Definitions", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                **Offensive Metrics:**
                - **Game_Pace**: Combined avg plays per game
                - **Pass_Att**: Average pass attempts per game
                - **ITT**: Implied Team Total (Vegas)
                - **EPA**: Expected Points Added per play
                - **YPP_Off**: Yards per play (offense)
                - **PTD_Off**: Points per drive (offense)
                """)
            with col2:
                st.markdown("""
                **Defensive Metrics:**
                - **DCR_Off**: Down conversion rate
                - **YPP_Def_Allow**: Yards per play allowed by opponent defense
                - **PTD_Def_Allow**: Points per drive allowed by opponent defense
                
                💡 **Green** = High/Good | **Red** = Low/Poor
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
        
        # Apply styling
        styled_matchups = (
            matchup_df
            .style
            .format("{:.1f}", subset=["Game_Pace", "Pass_Att", "ITT"])
            .format("{:.3f}", subset=["EPA"])
            .format("{:.2f}", subset=["YPP_Off", "PTD_Off", "DCR_Off", "YPP_Def_Allow", "PTD_Def_Allow"])
            .map(matchup_rag(matchup_df, "Game_Pace"), subset=["Game_Pace"])
            .map(matchup_rag(matchup_df, "Pass_Att"), subset=["Pass_Att"])
            .map(matchup_rag(matchup_df, "ITT"), subset=["ITT"])
            .map(matchup_rag(matchup_df, "EPA"), subset=["EPA"])
            .map(matchup_rag(matchup_df, "YPP_Off"), subset=["YPP_Off"])
            .map(matchup_rag(matchup_df, "PTD_Off"), subset=["PTD_Off"])
            .map(matchup_rag(matchup_df, "DCR_Off"), subset=["DCR_Off"])
            .map(matchup_rag(matchup_df, "YPP_Def_Allow"), subset=["YPP_Def_Allow"])
            .map(matchup_rag(matchup_df, "PTD_Def_Allow"), subset=["PTD_Def_Allow"])
        )
        
        st.dataframe(styled_matchups, width="stretch")
        
        st.download_button(
            "📥 Download Matchup Analysis CSV",
            data=matchup_df.to_csv(index=False),
            file_name="game_matchup_analysis.csv",
            mime="text/csv",
            key="download_matchups"
        )
    else:
        st.warning("⚠️ No matchup data available")