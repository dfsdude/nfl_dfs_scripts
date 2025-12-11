# DFS Tools Suite - Future Enhancements Plan

## High Priority

### Data & Projections
- [ ] **Integrate FantasyPros Advanced Stats** (In Progress)
  - [x] Web scraper built (`scrape_fantasypros.py`) with Chrome remote debugging
  - [x] Automated weekly data collection (QB, RB, WR, TE) for weeks 1-14
  - [ ] **Data Integration Pipeline**:
    - [x] Create `load_advanced_stats.py` - Load and merge FantasyPros CSVs with existing data ✅ COMPLETED
    - [x] Add player name matching/fuzzing between FantasyPros and DK formats ✅ COMPLETED
      - **Implemented Features**:
        - Fuzzy name matching with 85% similarity threshold
        - Exact + fuzzy matching: 75.9% match rate (465/613 players)
        - Manual name mappings for common variations
        - Team-based filtering to avoid false positives
        - Normalization: suffixes (Jr., III), apostrophes, common nicknames
        - Position-specific loading (QB, RB, WR, TE)
        - Recent weeks aggregation (customizable lookback)
        - Direct integration with DK salaries
      - **Test Results** (`utils/test_advanced_stats_integration.py`):
        - ✅ 8,570 player-week records loaded
        - ✅ 613 players aggregated (4-week avg)
        - ✅ 465 matched with DK salaries (464 exact, 1 fuzzy)
        - ✅ Breakdown: 58 QB, 120 RB, 179 WR, 108 TE
      - **Usage**: `from data.load_advanced_stats import load_all_advanced_stats, merge_with_dk_salaries`
    - [ ] Weekly data refresh automation (scheduled task or manual trigger)
    - [x] **Migrate Matchup.csv to odds.csv format** ✅ COMPLETED:
      - Updated `data/data_loader.py`: `load_matchups()` reads odds.csv and transforms to expected format
      - Transformation creates 2 rows per game (home as Init, away as Init)
      - Calculations: Spread from Init perspective, ITT = (Total/2) + (Spread/2)
      - Updated `roo_simulator.py` to use `load_matchups()` from data_loader
      - Updated `modules/top_stacks.py` to use `load_matchups()` with fallback
      - Test script `utils/test_matchup_migration.py` validates transformation
      - Results: 16 games → 32 matchup rows (bidirectional), verified spread symmetry and ITT calculations
      - Benefits: Real-time odds via API, moneyline data available, automated updates
    - [x] **Update correlation_model.py to use FantasyPros data** ✅ COMPLETED:
      - Added `load_fantasypros_data()` function to load all 4 position CSVs
      - Updated `build_team_player_roles()` to use FantasyPros columns (ATT, TGT, REC)
      - Role detection now uses actual weekly usage data:
        - QB1: Most pass attempts (ATT)
        - WR1/WR2: Top 2 by targets (TGT)
        - TE1: Most targets among TEs (TGT)
        - RB1: Most touches (ATT + REC)
      - **Results**:
        - ✅ 8,570 player-week records loaded
        - ✅ 33 teams with full role assignments
        - ✅ 330 team-week rolling correlations (5-week window)
        - ✅ Mean QB-WR1 correlation: 0.416 (13 strong positive, 12 moderate)
      - **Benefits**:
        - Week-by-week granularity (vs aggregated season stats)
        - More accurate role detection from actual usage
        - Better correlation trends with 14 weeks of data
        - Rolling windows show correlation evolution
      - Backward compatible: Still accepts Weekly_Stats.csv format
  - [x] **Feature Engineering** - Derive advanced metrics: ✅ COMPLETED
    - **Implementation**: Created `advanced_metrics.py` with position-specific feature engineering
    - **QB Metrics**: 
      - Pressure rate: (SACK+KNCK+HRRY)/(ATT+SACK) - mean 0.095
      - Deep ball rate: 20+ YDS / ATT
      - Accuracy score: (ATT-POOR-DROP)/ATT
      - Big play rate: (30+40+50 YDS)/ATT
      - Pressure vs avg: position-relative metric
    - **RB Metrics**:
      - Contact efficiency: YACON/ATT - mean 5.1 for elite backs
      - Broken tackle rate: BRKTKL/touches - mean 0.024
      - Receiving back score: REC/touches (0=rusher, 1=receiver)
      - Before contact efficiency: YBCON/ATT
      - Red zone usage: RZ TGT/touches
    - **WR/TE Metrics**:
      - Target quality: AIR/TGT (depth of target) - mean 5.41 yards
      - Catchable rate: CATCHABLE/TGT (QB accuracy)
      - Drop rate: DROP/CATCHABLE (player hands)
      - Route efficiency: YDS/AIR (gained vs targeted)
      - YAC per reception: position-relative separation
      - Contact balance: YACON/REC
      - Red zone target share: RZ TGT/TGT
    - **Results**: All metrics calculated on 8,570 player-week records
    - **Usage**: `from advanced_metrics import add_all_advanced_metrics`
  - [ ] **UI Integration**:
    - [ ] Add "Advanced Stats" tab to player detail views
    - [ ] Enhanced filtering (e.g., "RBs with >2 BRK TKL/game", "WRs with >8 YAC/R")
    - [ ] Volatility indicators from game-to-game variance (std dev of weekly stats)
  - [ ] **Projection Enhancement**:
    - [x] Weight advanced stats into ROO projections (e.g., pressure rate → QB downside) ✅ COMPLETED
      - **Implementation**: Created `projection_adjustments.py` with position-specific adjustments
      - **Phase 1 Results**:
        - QB adjustments: Pressure rate (-8%), deep ball rate (+5%), accuracy score
        - RB adjustments: Contact efficiency (+15%), broken tackle rate (+12%), receiving back score (+8%)
        - WR/TE adjustments: Target quality (+10%), catchable rate (+5%), drop rate, YAC (+8%), red zone targets (+12%)
        - Integration: Applied before Monte Carlo simulation in `roo_simulator.py`
        - New output columns: `advanced_stats_multiplier`, `combined_multiplier`
      - **Test Results**: 261/304 players matched (85.9%), 252 with adjustments applied (82.9%)
        - QB: Avg multiplier 0.945 (15 downgraded due to pressure)
        - RB: Avg multiplier 0.975 (8 upgraded for elite efficiency)
        - WR: Avg multiplier 1.088 (58 upgraded for target quality)
        - TE: Avg multiplier 1.076 (29 upgraded for red zone usage)
      - **Fix Applied**: Corrected player name normalization in `correlation_model.py` (removed team suffix)
      - **Match Rate**: 85.9% (up from initial 8.9% before fix)
    - [x] Target share trends (% TM week-over-week changes) ✅ COMPLETED
      - **Implementation**: Phase 2 in `projection_adjustments.py`
      - **Metrics**: 
        - Target share trend: Week-over-week % TM change
        - Role momentum: -1 to +1 scale (rising vs declining roles)
        - Identifies salary lag opportunities (role up, price hasn't adjusted)
      - **Application**: ±5% adjustment to projections based on momentum
      - **Output columns**: `target_share_trend`, `role_momentum`
    - [ ] **Accurate DK Points Calculation** - Replace proxy scoring with official DraftKings scoring
      - **Current Issue**: 
        - FantasyPros data doesn't include DK fantasy points
        - correlation_model.py uses rough proxy (YDS/25 + RTG/30 for QB, etc.)
        - Historical analysis and projections use inaccurate scoring
      - **Implementation Plan**:
        1. Create `dk_scoring.py` module based on `docs/dk_scoring.md` spec
        2. **Offensive Scoring Function**:
           - Passing: YDS/25 + TD*4 + INT*-1 + 300yd bonus (+3)
           - Rushing: YDS/10 + TD*6 + 100yd bonus (+3)
           - Receiving: REC*1 + YDS/10 + TD*6 + 100yd bonus (+3)
           - Other: Return TD (+6), Fumble Lost (-1), 2PT (+2)
        3. **DST Scoring Function**:
           - Defense: Sack (+1), INT (+2), Fum Rec (+2), Safety (+2), Blocked Kick (+2)
           - TDs: INT TD (+6), Fum TD (+6), Return TD (+6), Blocked TD (+6)
           - Points Allowed: 0 (+10), 1-6 (+7), 7-13 (+4), 14-20 (+1), 21-27 (0), 28-34 (-1), 35+ (-4)
        4. **Integration Points**:
           - Update `correlation_model.py`: Replace dk_points proxy with accurate calculation
           - Update `advanced_metrics.py`: Recalculate all metrics with correct DK points
           - Update `load_advanced_stats.py`: Add DK scoring to FantasyPros data on load
           - Validate: Recompute correlations with accurate scoring (expect 5-10% change)
        5. **Data Requirements**:
           - Map FantasyPros columns to DK scoring inputs
           - QB: YDS→pass_yds, TD→pass_tds, INT→pass_int, ATT/YDS→rush stats
           - RB: ATT/YDS→rush, REC/YDS→receiving, TD breakdown needed
           - WR/TE: REC/YDS/TD from FantasyPros
           - Handle missing stats (treat as 0)
        6. **Testing**:
           - Compare calculated DK points vs Weekly_Stats.csv DK_Points column
           - Validate bonus logic (300yd pass, 100yd rush/rec)
           - Spot-check high-scoring weeks (QB 30+ pts, WR 25+ pts)
      - **Expected Impact**:
        - More accurate correlations (QB-WR, WR-WR, RB-passing game)
        - Better ceiling/floor projections (bonuses affect upside)
        - Improved value identification (players underpriced for TD upside)
        - Historical analysis matches actual DK contest results
      - **Validation Metrics**:
        - Correlation accuracy: Before vs after with actual DK results
        - Projection RMSE: Test on historical weeks
        - Bonus frequency: % of games with 300yd/100yd bonuses
    - [ ] Game environment overlays (YAC backs in fast-paced games)
  - [ ] **Mispriced Player Identification**:
    - [ ] Value Score Algorithm:
      - ROO projection vs DK salary efficiency (pts per $1K)
      - Ceiling score (boom% potential) vs salary
      - Ownership arbitrage (low owned + high projection)
      - Correlation-adjusted value (stacking upside)
    - [ ] Market Inefficiency Detection:
      - Salary lag: Players with role changes not reflected in price
      - Matchup mispricing: Soft defense matchups undervalued
      - Game environment edge: Pace/total mispricing
      - Injury discount: Over-penalized for minor injuries
      - Recency bias: Over-reaction to 1-week variance
    - [ ] Advanced Stats Arbitrage:
      - High target share but low salary (WR/TE value)
      - Elite contact metrics but low RB salary (efficiency edge)
      - Low pressure rate QBs underpriced vs matchup
      - High broken tackle rate backs in soft run defenses
    - [ ] Implementation:
      - Automated value alerts (top 10 mispriced per position)
      - Value tier classification (S/A/B/C tiers)
      - Export to "Value Plays" CSV for quick reference
      - Integration with lineup builder (auto-suggest value)
    - [ ] Validation Metrics:
      - Historical ROI tracking by value score
      - Hit rate analysis (% of value plays that smash)
      - Salary efficiency correlation with cashing
- [ ] Add multiple projection source support (4for4, RotoGrinders for consensus)
- [ ] Implement projection consensus/weighted averaging
- [ ] Add injury status integration with real-time updates
- [ ] Weather data integration for outdoor games
- [ ] Practice participation tracking (DNP, Limited, Full)

### Top Stacks Tool
- [ ] Add RB correlation to QB (rushing TDs in high-scoring games)
- [ ] Implement negative correlation warnings (WR1 vs WR2 cannibalization)
- [x] **Add game script projections (blowout likelihood)**
  - **Implementation approach**:
    - Use existing data: Spread, Total, ITT (Implied Team Total)
    - Calculate blowout probability using spread distribution (std dev ~13.5 points)
    - Identify games with >70% chance of 14+ point margin
  - **Game script categories**:
    - 🔥 Blowout (Fav) - Favorite in lopsided game
    - ❄️ Blowout (Dog) - Underdog in lopsided game
    - ⚡ Shootout - High-scoring game (total ≥50)
    - ⚖️ Competitive - Close game, balanced
    - 🛡️ Low-Scoring - Defensive battle (total <44)
  - **Player impacts**:
    - Favorites in blowouts: RB +20%, WR -5% (run clock)
    - Underdogs in blowouts: QB +10%, WR +8% (garbage time), DST +25%
    - Shootouts: QB +15%, WR +12%, TE +8%
    - Low-scoring: DST +15%, RB +5%, QB -10%
  - **Columns added**:
    - `Script_Cat`: Game script category with emoji
    - `Script_Impact`: Position-specific multiplier (0.80-1.25)
    - `Blowout_Prob%`: Probability of 14+ point margin
  - **No new data required** - uses existing Matchup.csv (Spread, Total, ITT)
- [x] Include leverage score enhancements (boom% - ownership%)
- [ ] Add stack optimizer (auto-generate optimal QB+bring-back combos)

### Lineup Simulator
- [ ] Add multi-entry bankroll management
- [ ] Implement Kelly Criterion for optimal exposure
- [ ] Add lineup diversity metrics (uniqueness score)
- [ ] Support for showdown/single-game contests
- [ ] Live in-game win probability updates

### Pre-Contest Simulator
- [ ] Add correlation matrix visualization (heatmap)
- [ ] Implement exposure caps by position
- [ ] Add player pool optimizer (optimal 20-player pool)
- [ ] Risk tolerance profiles (conservative/balanced/aggressive)

### Ownership Adjuster
- [ ] Add late swap recommendations (ownership projection changes)
- [ ] Implement contrarian ownership targets
- [ ] Add field leverage calculator
- [ ] Historical ownership accuracy tracking

## Medium Priority

### New Tools
- [ ] **Lineup Builder** - In-app optimizer with stacking rules
- [ ] **Game Log Analyzer** - Player consistency/volatility viewer
- [ ] **Prop Bet Simulator** - TD scorer, yardage props
- [ ] **DFS News Feed** - Aggregated injury/lineup news

### Performance Optimization
- [ ] Cache ROO projections (only regenerate on data changes)
- [ ] Parallelize simulation loops (multiprocessing)
- [ ] Add GPU acceleration for 100K+ sim contests
- [ ] Implement incremental data loading (lazy load)

### UI/UX Enhancements
- [ ] Dark mode theme option
- [ ] Export all views to PDF/Excel
- [ ] Add keyboard shortcuts for power users
- [ ] Mobile-responsive layout
- [ ] Drag-and-drop file uploads

### Data Pipeline
- [ ] Automated data scraping (Vegas lines, weather)
- [ ] DraftKings API integration (live ownership, contest entries)
- [ ] Historical data warehouse (SQLite/PostgreSQL)
- [ ] Automated Weekly_Stats.csv updates from NFL API

## Low Priority

### Analytics
- [ ] ROI tracking by player, position, game environment
- [ ] Win rate analysis by stack type
- [ ] Chalk vs leverage performance tracking
- [ ] Field construction analysis (what the field looks like)

### Advanced Features
- [ ] Machine learning projection models (XGBoost, LightGBM)
- [ ] Neural network correlation predictions
- [ ] Reinforcement learning for lineup construction
- [ ] Natural language query interface ("Show me cheap RBs in high totals")

### Integration
- [ ] Discord bot for alerts and quick queries
- [ ] Slack integration for team collaboration
- [ ] API for external tool integration
- [ ] Chrome extension for DraftKings site integration

## Research & Experimentation

### Modeling Improvements
- [ ] Time-of-season adjustments (playoffs, weather months)
- [ ] Opponent-adjusted metrics (vs top-10 defense)
- [ ] Coaching tendencies (play-calling aggressiveness)
- [ ] Rest/travel factors (West coast to East coast)
- [ ] Altitude adjustments (Denver games)

### Simulation Enhancements
- [ ] Multi-sport support (NBA, MLB, NHL)
- [ ] In-play simulation (update after 1pm games)
- [ ] Conditional probability (if Player A scores, what happens to Player B)
- [ ] Game theory optimal (GTO) lineup construction

## Completed ✅
- [x] Unified app with single launch point
- [x] DST full integration (name standardization, volatility)
- [x] Full season data for max_dk and avg_dk
- [x] Lineup simulator DST name mapping
- [x] Boom/Bust salary and ownership filters
- [x] ROO projections with PROE integration
- [x] Correlation model (QB-WR, WR-WR)
- [x] Game environment simulation
- [x] Contest-specific payout structures
- [x] DST hits_4x calculation from Weekly_DST_Stats
- [x] Leverage score enhancements (filter, sort, categories, insights)
- [x] **FantasyPros Advanced Stats Scraper**
  - Automated Selenium scraper with Chrome remote debugging
  - Collects 14 weeks of advanced stats for QB, RB, WR, TE
  - 8,570+ total player-week records (1,082 QB, 2,201 RB, 3,302 WR, 1,985 TE)
  - Output: Position-specific CSVs with 20-26 advanced metrics per position

## Notes

**Priority Criteria**:
- **High**: Directly impacts win rate or user workflow efficiency
- **Medium**: Quality of life improvements or new capabilities
- **Low**: Nice-to-have features or experimental

**Implementation Order**:
1. Focus on data quality and projection accuracy first
2. Then optimize simulation performance
3. Finally add new tools and advanced features

**Review Frequency**: Update this plan monthly after each contest cycle
