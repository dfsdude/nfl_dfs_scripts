# DFS Tools Suite - Future Enhancements Plan

## High Priority

### Data & Projections
- [ ] Add multiple projection source support (FantasyPros, 4for4, RotoGrinders)
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
