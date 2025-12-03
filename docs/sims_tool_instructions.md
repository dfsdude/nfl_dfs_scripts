0. High-level architecture

You (the coding agent) are building a module (ideally inside a Streamlit app) that does:

Ingest data

players.csv – current-week projections + external ownership.

Weekly Stats.csv – historical per-game DK points and usage.

matchup.csv – game-level totals / spreads / efficiency.

lineups.csv – the user’s lineups to evaluate.

Precompute

Per-player outcome distributions (based on Weekly Stats + players.csv projections).

Per-team game environment model (based on matchup.csv).

Simulate the slate N times

Simulate game environments (team points, volatility).

Sample player scores, respecting game/team context and correlations.

Generate / reuse a pool of field lineups based on external ownership.

Rank user lineups vs field for each sim.

Assign contest payouts and compute profit.

Summarize for each user lineup

Mean score, mean profit, ROI.

Probabilities of cashing, top 10%, top 1%, 1st place, etc.

Optional: distribution plots.

You do not build ownership projections. You simply trust the ownership column in players.csv.

1. Data ingestion: what each file means
1.1 players.csv (current slate)

Columns:

Player,Position,Team,Salary,Prev Wk Sal,dk_ownership,
median_proj,ceiling_proj,Player Value (Pts per $1k),
Avg DK,Max DK,Var DK,4x Hits


Instructions:

Read into players_df.

Expect that one column holds external projected ownership (e.g. from OWS).

You can either:

Add a column manually called Proj_Own before running sims, or

Overload dk_ownership as “this week projected ownership” (your choice; just be consistent).

Treat this ownership column as the field exposure; do not re-estimate it.

1.2 Weekly Stats.csv (historical outcomes)

Schema:

DK_List,Week,Target Share,Weighted_Opps,Rush Efficiency,
YdsPerTar,Passer Rating,Position,Team,DK_Points


Instructions:

Load into weekly_df.

Each row = one historical game for that player (DK_List) with fantasy output DK_Points.

This is your primary range-of-outcomes source.

1.3 matchup.csv (game environment)

Schema (team-centric rows):

Game,Init,ITT,Loc,FavStatus,Opp,Opp_ITT,OppStatus,
Total,Spread,
Init_EPA_Play,Init_Yards Per Play,Init_Points Per Drive,
Init_Explosive Play Rate,Init_Down Conversion Rate,
Opp_EPA_Play_Allowed,Opp_Yards Per Play Allowed,
Opp_Points Per Drive Allowed,Opp_Explosive Play Rate Allowed,
Opp_Down Conversion Rate Allowed


Instructions:

Load into matchup_df.

Each row = team-level view of a game (Init = team, Opp = opponent).

Use this to build team environment objects and per-sim game outcomes.

1.4 lineups.csv (user lineups)

Define a simple format (you’ll enforce it in Streamlit):

LineupID,Player1,Player2,...,Player9


Where each PlayerX matches Player names in players.csv.

Load into lineups_df.

2. Build player↔stats↔matchup mapping
2.1 Map players ↔ weekly stats

Key:

(Player == DK_List) AND (Team == Team) AND (Position == Position)


Steps:

For each row in players_df, find matching rows in weekly_df.

Build a dict:

player_hist[player_id] = {
    "scores": [DK_Points_i],
    "weeks": [Week_i],
    "target_share": [...],
    "weighted_opps": [...],
    "position": Position,
    "team": Team,
}


where player_id can be (Player, Team, Position) or a simple string if unique.

Track num_games per player.

2.2 Map players ↔ matchup teams

Key:

players_df.Team == matchup_df.Init


Steps:

Build a team_env dict (per team):

team_env[Init] = {
    "game_id": Game,
    "opp": Opp,
    "itt": ITT,
    "total": Total,
    "spread": Spread,
    "loc": Loc,
    "fav_status": FavStatus,
    "off_epa": Init_EPA_Play,
    "off_ypp": Init_Yards Per Play,
    "off_ppd": Init_Points Per Drive,
    "off_explosive": Init_Explosive Play Rate,
    "off_conv": Init_Down Conversion Rate,
    "def_eppa": Opp_EPA_Play_Allowed,
    "def_yppa": Opp_Yards Per Play Allowed,
    "def_ppda": Opp_Points Per Drive Allowed,
    "def_explosive_allowed": Opp_Explosive Play Rate Allowed,
    "def_conv_allowed": Opp_Down Conversion Rate Allowed,
}


Build game_to_teams[Game] = (teamA, teamB) for quick lookup.

3. Build per-player historical metrics & distributions
3.1 Recency-weighted history

For each player with ≥ 1 weekly record:

Let scores = list of DK_Points.

Let weeks = list of Week.

Compute a recency weight:

max_week = max(weeks)
lambda_ = 0.15  # decay parameter, configurable
weights_i = exp( -lambda_ * (max_week - Week_i) )


Store:

hist = {
    "scores": scores,
    "weights": weights,
}

3.2 Historical mean / variance / ceiling

Using weights:

Mean:

mean_hist = sum(w_i * s_i) / sum(w_i)


Variance / std dev:

var_hist = sum(w_i * (s_i - mean_hist)**2) / sum(w_i)
std_hist = sqrt(var_hist)


90th percentile (weighted):

Sort (score, weight) pairs by score ascending, accumulate weights, stop when cumulative weight ≥ 0.9.

Store per player:

player_metrics[player_id] = {
    "mean_hist": mean_hist,
    "std_hist": std_hist,
    "ceil_hist_90": ceil_90,
    "num_games": len(scores),
}

3.3 Fallback for sparse / no history

For players with little/no data:

Group other players by (Position, salary_bucket) to build position/salary archetypes.

Define salary buckets: e.g. 3–4k, 4–5k, 5–6k, 6–7k, 7k+.

Compute average mean_hist, std_hist in each bucket.

For a player with num_games < 3:

Use bucket-level mean/std if available.

Otherwise use a global position average.

4. Turn historical data + projections into per-player sampling functions

We want, for each player, a function:

sample_player_score(player_id, env_state, rng) -> float

4.1 Base empirical + scaling

For players with enough history (num_games >= 6):

Use empirical scores with recency weights as a discrete distribution.

Align to this week’s median projection (median_proj from players.csv):

Let mean_hist from metrics.

Let median_proj from players_df.

scale = median_proj / max(mean_hist, small_number)


Base sampling (before environment & correlation):

raw_score ~ empirical(scores, weights)
base_score = raw_score * scale

4.2 Parametric fallback (normal/lognormal)

For low-sample players or when you decide not to use pure empirical:

Use median_proj, ceiling_proj, and Var DK (if present) to fit a distribution.

Simple approach:

Assume normal for now:

Mean ≈ median_proj.

Std dev ≈ max( sqrt(Var DK), position_min_std ).

Then:

base_score ~ max( Normal(mean, std), 0 )


You can upgrade to lognormal later if needed.

4.3 Volatility classification (optional but nice)

Use std_hist / mean_hist and usage stats (Target Share, Weighted_Opps from Weekly Stats) to tag:

HighVolume / MediumVolume / LowVolume

HighVolatility / MediumVolatility / LowVolatility

Use those tags to tweak tails (e.g. increase std for LowVolume / HighVolatility players).

5. Game environment engine using matchup.csv

You need a function to simulate the per-game environment each sim.

5.1 Precompute team matchup strength and volatility

Using team_env:

Compute z-scores across all teams for:

off_epa, off_ypp, off_ppd, off_explosive, off_conv.

def_eppa, def_yppa, def_ppda, def_explosive_allowed, def_conv_allowed.

Offensive strength:

off_strength = (
    0.3 * z(off_epa) +
    0.2 * z(off_ypp) +
    0.2 * z(off_ppd) +
    0.15 * z(off_explosive) +
    0.15 * z(off_conv)
)


Matchup-easiness (defense they face):

def_matchup = (
    0.3 * (-z(def_eppa)) +
    0.2 * (-z(def_yppa)) +
    0.2 * (-z(def_ppda)) +
    0.15 * (-z(def_explosive_allowed)) +
    0.15 * (-z(def_conv_allowed))
)


Combined offensive vs matchup index:

ovr_matchup_strength = z(off_strength + def_matchup)


Volatility index:

volatility_raw = z(off_explosive) + z(def_explosive_allowed)
volatility_z = z(volatility_raw)


Store for each team:

team_env[team]["ovr_matchup_strength"] = ovr_matchup_strength
team_env[team]["volatility_z"] = volatility_z
team_env[team]["base_points"] = ITT
team_env[team]["spread"] = Spread
team_env[team]["total"] = Total

5.2 Per-sim game environment

For each sim, for each Game:

Get the two teams T1, T2.

Baseline:

total_base = Total
spread_base = team_env[T1]["spread"]  # + means T1 favored
t1_base = team_env[T1]["base_points"]
t2_base = team_env[T2]["base_points"]


Sample noise:

total_sd = 7.0   # configurable
spread_sd = 4.0  # configurable

total_sim  = Normal(total_base, total_sd)
spread_sim = Normal(spread_base, spread_sd)


Convert to team totals:

t1_points_sim = (total_sim / 2.0) + (spread_sim / 2.0)
t2_points_sim = total_sim - t1_points_sim


Apply matchup strength:

alpha = 0.05  # impact of matchup strength

m1 = 1.0 + alpha * team_env[T1]["ovr_matchup_strength"]
m2 = 1.0 + alpha * team_env[T2]["ovr_matchup_strength"]

t1_points_sim *= m1
t2_points_sim *= m2

# renormalize back to total_sim
total_adj = t1_points_sim + t2_points_sim
if total_adj > 0:
    renorm = total_sim / total_adj
    t1_points_sim *= renorm
    t2_points_sim *= renorm


Store in env_state for this sim:

env_state[game_id] = {
    "points": {T1: t1_points_sim, T2: t2_points_sim},
    "total_sim": total_sim,
    "spread_sim": spread_sim,
    "team_scoring_mult": {
        T1: t1_points_sim / max(team_env[T1]["base_points"], small),
        T2: t2_points_sim / max(team_env[T2]["base_points"], small),
    },
    "volatility_z": {
        T1: team_env[T1]["volatility_z"],
        T2: team_env[T2]["volatility_z"],
    }
}

6. Apply environment & correlation at player level
6.1 Environment multiplier

When sampling a player’s score:

Identify team for that player.

Get game_id and team_scoring_mult from env_state.

After drawing base_score from the player’s distribution:

team_mult = env_state[game_id]["team_scoring_mult"][team]
score_after_env = base_score * team_mult

6.2 Correlation logic

You don’t have to be perfect; just avoid wildly unrealistic worlds.

Examples:

QB + WR/TE correlation

If a QB’s score_after_env > 1.5 × his median_proj, then for his primary pass-catchers (same team, WR/TE with high weighted_opps/target_share):

Resample or nudge their scores upward (e.g. multiply by factor between 1.1–1.3, or sample from higher quantiles).

If QB nukes (score < 0.5 × median), nudge pass-catchers down.

RB + team total

If team_scoring_mult is very high:

Slightly increase RB scores, especially for high-volume RBs.

If very low, reduce them.

DST + spread

If spread_sim strongly favors a team (e.g. < -7 or > +7 depending on sign convention), give that team’s DST a higher chance of spiking:

Slight multiplier based on being a big favorite.

Implement this as simple, deterministic adjustments layered on top of base_score × team_mult.

7. Field lineups using external ownership

You do not compute ownership. Instead:

Assume players_df has column Proj_Own (percentage), coming from OWS or similar.

7.1 Reduced field size for sims

Choose a sim-field size F' (e.g. 20,000 lineups) representing the real field (e.g. 200,000):

This is just for simulation; EV will scale.

7.2 Generate field lineup pool

You need a function like:

generate_field_lineups(players_df, F_prime, rng) -> list_of_lineups


Constraints:

DK classic: 9 spots, salary ≤ 50,000.

Position constraints: 1 QB, 2–3 RB, 3–4 WR, 1 TE, 1 DST (or exactly defined slots).

Ownership-weighted sampling:

Convert Proj_Own into relative weights per position.

For each lineup:

Fill slots by sampling players (within the position pool) with probability proportional to Proj_Own (and maybe a small random noise).

Enforce salary cap and no duplicates in a lineup.

Deduplicate lineups if desired.

You can generate this pool once and reuse it in all sims to save time.

8. Sim loop and contest EV
8.1 Inputs

players_df with distributions + Proj_Own.

team_env from matchup.csv.

field_lineups (size F′).

user_lineups from lineups.csv.

Contest config:

field_size (real full field, e.g. 200k).

payout_structure (array or list mapping rank → payout).

entry_fee.

N_sims (e.g. 5k–20k).

8.2 Per-sim workflow

For each sim s:

Build env_state for all games (as in section 5.2).

For each player:

Sample base_score from their distribution.

Apply environment multiplier (team_scoring_mult).

Apply correlation adjustments.

Store sim_score[player_id].

Score lineups:

For each field lineup:

Sum scores of included players → score_field[i].

For each user lineup:

Sum scores → score_user[j].

Rank all lineups (field + user) by score, descending:

Compute rank_user[j] for each user lineup.

Map rank_user[j] to payouts using payout_structure and field_size:

Profit = payout - entry_fee.

Record per-sim:

score_user[j], rank_user[j], profit_user[j].

8.3 Aggregation over sims

After all sims:

For each user lineup:

mean_score

mean_profit

ROI = mean_profit / entry_fee

prob_cash = fraction of sims with profit > 0

prob_top10 = fraction of sims rank ≤ 10

prob_top1 = fraction of sims rank ≤ 0.01 * field_size

prob_first = fraction of sims rank == 1

min_profit, max_profit

Return a summary DataFrame with one row per lineup and these metrics.

9. Streamlit integration (just behavior, not code)

In Streamlit:

Inputs:

File uploaders for players.csv, Weekly Stats.csv, matchup.csv, lineups.csv.

Numeric inputs / sliders:

N_sims

field_size

entry_fee

total_sd, spread_sd

alpha_matchup_strength

Maybe a checkbox for “use fancy correlation logic”.

On “Run Sims”:

Validate inputs.

Precompute player distributions and team_env.

Generate field lineups once.

Run sim loop.

Display:

Table of lineups with EV metrics.

For a selected lineup: histogram of profit and score.