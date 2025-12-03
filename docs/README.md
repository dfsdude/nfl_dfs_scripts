# 📚 DFS Tools Documentation

Complete documentation for the DFS Dude Tools suite.

## 🏗️ Architecture & Setup

### [MODULAR_STRUCTURE.md](MODULAR_STRUCTURE.md)
**Complete modular architecture guide** - Detailed explanation of the project structure, component organization, and best practices for extending the codebase.

### [MODULAR_REORGANIZATION.md](MODULAR_REORGANIZATION.md)
**Refactoring summary** - Step-by-step documentation of the modularization process, showing before/after comparisons and key improvements.

### [MODULARIZATION_SUMMARY.md](MODULARIZATION_SUMMARY.md)
**Code organization changes** - Summary of the transition from monolithic to modular architecture.

### [QUICK_START.md](QUICK_START.md)
**Fast setup guide** - Get up and running quickly with essential configuration and data setup.

---

## 🛠️ Tool Guides

### [top_stacks_stokastic.md](top_stacks_stokastic.md)
**Top Stacks tool methodology** - Comprehensive guide to stack analysis, boom/bust modeling, and correlation-aware optimization. Includes PROE integration and Sharp Football metrics.

### [sims_tool_instructions.md](sims_tool_instructions.md)
**Lineup Simulator guide** - Step-by-step instructions for running Monte Carlo simulations on your lineups against field competition.

### [review_sims_tool.md](review_sims_tool.md)
**Simulator review & improvements** - Technical analysis of the simulation engine with enhancement recommendations.

### [sim_tool_improvements.md](sim_tool_improvements.md)
**Simulator enhancements** - Log of improvements made to the lineup simulator.

### [ROO_README.md](ROO_README.md)
**ROO projections system** - Documentation for the Range of Outcomes (ROO) simulator that generates matchup-adjusted projections with floor/ceiling estimates.

---

## 📊 Feature Documentation

### [boom_bust_tool.md](boom_bust_tool.md)
**Boom/Bust methodology** - Explanation of percentile-based boom thresholds, position-specific targeting, and bust risk calculations.

### [ceiling_floor_projections.md](ceiling_floor_projections.md)
**Projection calculations** - Technical details on how floor (P15), median (P50), and ceiling (P85) projections are calculated from Monte Carlo simulations.

### [ownership_projections.md](ownership_projections.md)
**Ownership modeling** - How ownership percentages are adjusted to match DraftKings roster construction (900% total).

### [weighted_opportunity.md](weighted_opportunity.md)
**Opportunity metrics** - Explanation of weighted opportunity calculations that combine touches, targets, and snap counts to predict usage.

---

## 🔧 Technical Details

### [DST_INTEGRATION.md](DST_INTEGRATION.md)
**Defense/Special Teams handling** - Technical implementation of DST projections, matchup adjustments, and scoring variance.

### [NEW_DATA_STRUCTURE.md](NEW_DATA_STRUCTURE.md)
**Data pipeline overview** - Complete guide to the CSV data structure, required columns, and data flow through the tools.

### [PIPELINE_SIMPLIFICATION.md](PIPELINE_SIMPLIFICATION.md)
**Pipeline improvements** - Documentation of optimizations made to the data loading and processing pipeline.

### [UNIFIED_APP.md](UNIFIED_APP.md)
**Unified application** - Guide to the multipage Streamlit app that provides a single launch point for all tools.

### [modular_instructions.md](modular_instructions.md)
**Modular architecture instructions** - Original guidelines used to restructure the codebase into a clean, modular architecture.

---

## 🔍 Change Logs

### [OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)
**Performance optimizations** - Log of performance improvements including caching, vectorization, and algorithm enhancements.

---

## 📖 Quick Reference

### Common Tasks

**Generate Projections:**
```bash
python roo_simulator.py
```

**Launch All Tools:**
```bash
streamlit run app.py
```

All tools are now accessed exclusively through the unified app with sidebar navigation.

### Data Files Location
All CSV data files should be in: `C:\Users\schne\Documents\DFS\2025\Dashboard\`

### Key Configuration Files
- `utils/config.py` - Centralized configuration
- `utils/constants.py` - Position mappings, roster construction
- `utils/helpers.py` - Utility functions

---

## 🤝 Contributing

When adding new features or tools:

1. **Follow the modular structure** - See [MODULAR_STRUCTURE.md](MODULAR_STRUCTURE.md)
2. **Use existing components** - Leverage `components/`, `services/`, `data/`, `utils/`
3. **Add documentation** - Create a new .md file in this folder
4. **Update this index** - Add your new documentation to the appropriate section

---

**Last Updated**: December 3, 2025
