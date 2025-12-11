DraftKings NFL Classic – Scoring Specification for Coding Agent

This document defines the precise DraftKings NFL Classic scoring system.
Your job (coding agent) is to implement functions that compute fantasy points from weekly player-level stats for both offensive players and DST.

Use this spec to ensure scoring is exact, consistent, and fully aligned with DraftKings rules.

1. Overview

In DraftKings NFL Classic contests:

Each player in a lineup earns points based on real-life NFL stats.

Each DST earns points based on defensive stats, special teams TDs, and points allowed.

Some bonuses (e.g., 300-yard passing, 100-yard rushing, etc.) apply.

This document breaks down the exact point values needed to compute fantasy points from weekly stats.

2. Offensive Player Scoring

These rules apply to QB, RB, WR, TE, and FLEX (RB/WR/TE).

## Passing
Stat	Points
Passing TD	+4 pts
Interception Thrown	–1 pt
Passing Yards	+1 pt per 25 yards (0.04 per yard)
300+ Yard Passing Bonus	+3 pts

Implementation notes:

Bonus is applied once per player if their passing yards ≥ 300.

## Rushing
Stat	Points
Rushing TD	+6 pts
Rushing Yards	+1 pt per 10 yards (0.1 per yard)
100+ Yard Rushing Bonus	+3 pts

Implementation notes:

Bonus is applied once per player if rushing yards ≥ 100.

## Receiving
Stat	Points
Reception	+1 pt
Receiving TD	+6 pts
Receiving Yards	+1 pt per 10 yards (0.1 per yard)
100+ Yard Receiving Bonus	+3 pts

Implementation notes:

Bonus is applied once per player if receiving yards ≥ 100.

## Other Offensive Stats
Event	Points
Punt/Kickoff/FG Return TD	+6 pts
Fumble Lost	–1 pt
2-Point Conversion (Pass, Run, or Catch)	+2 pts
Offensive Fumble Recovery TD	+6 pts

Implementation notes:

Passing a 2-point conversion counts as +2 for the passer.

Catching a 2-point conversion counts as +2 for the receiver.

Running one counts as +2 for the rusher.

3. Defense / Special Teams (DST) Scoring

DSTs earn points via defensive stats, special teams plays, and points allowed.

## Turnovers, Sacks, Returns, Safeties
Event	Points
Sack	+1 pt
Interception	+2 pts
Fumble Recovery	+2 pts
Punt/Kickoff/FG Return TD	+6 pts
Interception Return TD	+6 pts
Fumble Recovery TD	+6 pts
Blocked Punt or FG Return TD	+6 pts
Safety	+2 pts
Blocked Kick (punt, FG, XP)	+2 pts
2-point conversion or extra point returned	+2 pts
## Points Allowed (PA)

Points allowed is based on points the DST surrendered while on the field.

Points Allowed	DST Points
0	+10
1–6	+7
7–13	+4
14–20	+1
21–27	0
28–34	–1
35+	–4
Notes on Points Allowed:

Points Allowed includes:

Rushing TDs

Passing TDs

Offensive Fumble Recovery TDs

Punt Return TDs

Kick Return TDs

FG Return TDs

Blocked FG TDs

Blocked Punt TDs

2-point conversions

Extra points

Field goals

Points Allowed does not include:

Points surrendered by the team's offense (e.g., a pick-six thrown by their QB).

Special Case:

A fumble recovery is credited to the DST even if:

Their offense fumbles,

The opposing defense recovers,

Then the fumbling team recovers that ball back.

This results in a DST fumble recovery.

4. Lineup Structure (for completeness)

A DraftKings NFL Classic lineup must include 9 players from at least 2 different NFL games:

1 QB

2 RB

3 WR

1 TE

1 FLEX (RB/WR/TE)

1 DST

Salary cap: $50,000

(This is useful for your field lineup generator.)

5. Coding Agent Requirements

You (coding agent) must implement scoring functions:

## 5.1 Offensive scoring
def score_offensive_player(stats: dict) -> float:
    """
    stats includes:
        pass_yds, pass_tds, pass_int,
        rush_yds, rush_tds,
        rec_yds, rec_tds, receptions,
        fumbles_lost,
        two_pt_conversions (pass/run/catch),
        return_tds,
        offensive_fumble_td
    """

## 5.2 DST scoring
def score_dst(stats: dict) -> float:
    """
    stats includes:
        sacks, interceptions, fumble_recoveries,
        defensive_tds, return_tds,
        safeties, blocked_kicks,
        two_pt_returns,
        points_allowed
    """

## 5.3 Bonuses logic

Your scoring functions must apply:

300+ passing yards → +3

100+ rushing yards → +3

100+ receiving yards → +3

These bonuses are not position-restricted (e.g., a WR who gets 100 rushing yards would get the rushing bonus).

6. Example Calculations (for your testing)
## Example 1: WR line (hypothetical)

7 receptions → 7 pts

92 receiving yards → 9.2 pts

1 receiving TD → 6 pts

Total: 22.2 DK points

Since rec yards < 100 → no bonus.

## Example 2: QB line

312 passing yards → 312 / 25 = 12.48 pts

Passing bonus → +3

2 passing TDs → +8

1 INT → –1

24 rushing yards → +2.4

Total: 24.88 DK points

## Example 3: DST line

3 sacks → 3

1 interception → 2

1 fumble recovery → 2

Points allowed = 14 → +1

Total: 8 DK points

7. Implementation Notes

All yardage-based scoring should be calculated exactly to the decimal.

Bonuses are one-time additions.

Assume the upstream stats file gives raw numbers (yards, TDs, sacks, etc).

If a stat does not appear for a player, treat it as zero.

Ensure negative outcomes (interceptions, fumbles lost, points allowed penalty) are applied.