# DFS Tools Suite - Modular Architecture

## Directory Structure

```
dfsdude-tools/
│
├── app.py                      # Main entry point (Streamlit multipage)
├── launch_dfs_tools.bat        # Windows launcher
│
├── pages/                      # Streamlit pages (auto-discovered)
│   ├── 1_🏠_Home.py           # Home page with tool descriptions
│   ├── 2_⭐_Top_Stacks.py     # Top Stacks & Boom/Bust tool
│   ├── 3_📊_Lineup_Simulator.py
│   ├── 4_🎲_Pre_Contest_Simulator.py
│   └── 5_🦃_Ownership_Adjuster.py
│
├── components/                 # Reusable UI components
│   ├── __init__.py
│   ├── layouts.py             # Cards, metrics, expanders, filters
│   ├── charts.py              # Plotly visualizations
│   └── tables.py              # Styled dataframes, downloads
│
├── data/                       # Data loading & caching
│   ├── __init__.py
│   └── data_loader.py         # CSV loaders with @st.cache_data
│
├── services/                   # Business logic (no Streamlit)
│   ├── __init__.py
│   └── simulations.py         # Monte Carlo logic
│
├── utils/                      # Cross-cutting utilities
│   ├── __init__.py
│   ├── config.py              # App configuration
│   ├── constants.py           # Team mappings, positions
│   └── helpers.py             # Generic helpers
│
├── modules/                    # Legacy modularized tools
│   ├── __init__.py
│   ├── top_stacks.py          # Wrapped in run()
│   ├── sims_tool.py
│   ├── pre_contest_sim.py
│   └── ownership_adjuster.py
│
├── assets/                     # Static files
│   └── (logos, CSS, sample data)
│
├── Original Standalone Tools/
│   ├── top_stacks_tool.py     # Still work independently
│   ├── sims_tool.py
│   ├── pre_contest_simulator.py
│   └── ownership_adjuster.py
│
├── roo_simulator.py            # Data generation script
├── contest_analyzer.py         # Post-contest analysis
│
└── Documentation/
    ├── README.md
    ├── UNIFIED_APP.md
    ├── QUICK_START.md
    ├── MODULAR_STRUCTURE.md   # This file
    └── MODULARIZATION_SUMMARY.md
```

---

## Architecture Principles

### 1. **Separation of Concerns**

#### UI Layer (`components/`)
- Reusable Streamlit widgets
- No business logic
- Pure presentation

```python
# components/charts.py
def create_ownership_scatter(df, x_col, y_col, color_col):
    return px.scatter(df, x=x_col, y=y_col, color=color_col)
```

#### Business Logic (`services/`)
- Pure Python functions
- No Streamlit imports
- Easy to test

```python
# services/simulations.py
def run_player_simulations(mean, std, n_simulations):
    return np.random.normal(mean, std, n_simulations)
```

#### Data Layer (`data/`)
- Cached CSV loaders
- Data transformations
- ETL pipelines

```python
# data/data_loader.py
@st.cache_data(ttl=3600)
def load_weekly_stats():
    return pd.read_csv(DATA_DIR / "Weekly_Stats.csv")
```

---

### 2. **Streamlit Multi-Page App**

Streamlit automatically discovers pages in the `pages/` directory:

```
pages/
├── 1_🏠_Home.py          # Shows first
├── 2_⭐_Top_Stacks.py    # Shows second  
├── 3_📊_Lineup_Simulator.py
└── ...
```

**Benefits**:
- Automatic sidebar navigation
- No manual routing code
- Clean URL structure
- Back/forward button support

---

### 3. **Configuration Management**

Central configuration in `utils/config.py`:

```python
# Data directory
DATA_DIR = Path(r"C:\Users\schne\Documents\DFS\2025\Dashboard")

# ROO Simulator settings
ROO_CONFIG = {
    "n_simulations": 10000,
    "lookback_weeks": 8,
    ...
}

# Initialize app
def init_app_config():
    st.set_page_config(
        page_title="DFS Tools Suite",
        layout="wide"
    )
```

---

### 4. **Reusable Components**

#### Example: Metric Cards

```python
from components.layouts import create_three_column_metrics

metrics = [
    {"title": "ROI", "value": "145%", "delta": "+23%"},
    {"title": "Cash %", "value": "67%", "delta": "+12%"},
    {"title": "Avg Finish", "value": "324", "delta": "-89"}
]

create_three_column_metrics(metrics)
```

#### Example: Charts

```python
from components.charts import create_ownership_scatter

fig = create_ownership_scatter(
    df=players_df,
    x_col="Own%",
    y_col="FPTS",
    color_col="Position"
)
st.plotly_chart(fig)
```

#### Example: Tables

```python
from components.tables import display_styled_table

display_styled_table(
    df=results_df,
    highlight_columns={
        'ROI': {'type': 'background_gradient', 'cmap': 'RdYlGn'},
        'Boom%': {'type': 'bar', 'color': 'lightblue'}
    },
    title="Player Results"
)
```

---

## Usage

### Running the App

```bash
# Launch unified app (Streamlit multipage)
streamlit run app.py

# Or use batch file
launch_dfs_tools.bat
```

### Standalone Tools (Still Work)

```bash
streamlit run top_stacks_tool.py
streamlit run sims_tool.py
streamlit run pre_contest_simulator.py
streamlit run ownership_adjuster.py
```

---

## Creating a New Tool/Page

### Step 1: Create Page File

```python
# pages/6_🆕_New_Tool.py

import streamlit as st
from utils.config import init_app_config
from data.data_loader import load_roo_projections
from components.charts import create_floor_ceiling_chart

st.title("🆕 New Tool")

# Load data
df = load_roo_projections()

# Create visualization
fig = create_floor_ceiling_chart(df)
st.plotly_chart(fig)
```

### Step 2: Add Business Logic (if needed)

```python
# services/new_analysis.py

def calculate_custom_metric(df, param1, param2):
    """Pure Python logic - no Streamlit"""
    return df['col1'] * param1 + param2
```

### Step 3: Add Reusable Component (if needed)

```python
# components/custom_widget.py

import streamlit as st

def create_custom_display(data):
    with st.container():
        st.metric("Custom Metric", data['value'])
        st.progress(data['progress'])
```

That's it! Streamlit automatically discovers the new page.

---

## Benefits of Modular Structure

### ✅ Clean Code Organization
- Clear separation between UI, logic, and data
- Easy to find and modify code
- Consistent patterns across tools

### ✅ Reusability
- Components used across multiple pages
- No code duplication
- Faster development of new tools

### ✅ Testability
- Business logic in `services/` has no Streamlit
- Easy to write unit tests
- Mock data loading for tests

### ✅ Maintainability
- Changes in one place affect all tools
- Centralized configuration
- Easy to add new features

### ✅ Scalability
- Add new pages without touching existing code
- Modular components scale to many tools
- Clear extension points

---

## Migration Strategy

### Phase 1: ✅ Infrastructure (Complete)
- [x] Create directory structure
- [x] Build utility modules (`utils/`)
- [x] Build data loaders (`data/`)
- [x] Build reusable components (`components/`)
- [x] Build services (`services/`)
- [x] Create page structure (`pages/`)

### Phase 2: 🚧 Tool Refactoring (In Progress)
- [ ] Refactor Top Stacks to use modular components
- [ ] Refactor Lineup Simulator
- [ ] Refactor Pre-Contest Simulator
- [ ] Refactor Ownership Adjuster

### Phase 3: Enhancement
- [ ] Add shared state management
- [ ] Add export/import functionality
- [ ] Add integrated optimizer
- [ ] Add real-time updates

---

## Code Examples

### Loading Data

```python
from data.data_loader import load_all_data

# Load everything at once
data = load_all_data()

# Or load individually
from data.data_loader import load_roo_projections, load_matchups

roo_df = load_roo_projections()
matchups_df = load_matchups()
```

### Using Constants

```python
from utils.constants import TEAM_MAPPING, POSITIONS, ROSTER_CONSTRUCTION

# Map team abbreviations
full_name = TEAM_MAPPING['BUF']  # 'Bills'

# Iterate positions
for pos in POSITIONS:
    print(f"Position: {pos}")

# Roster requirements
qb_count = ROSTER_CONSTRUCTION['QB']  # 1
```

### Creating Visualizations

```python
from components.charts import (
    create_ownership_scatter,
    create_volatility_bar_chart,
    create_floor_ceiling_chart
)

# Ownership scatter
fig1 = create_ownership_scatter(df, 'Own%', 'FPTS', 'Position')
st.plotly_chart(fig1)

# Volatility bars
fig2 = create_volatility_bar_chart(df, 'Player', 'Volatility_Index')
st.plotly_chart(fig2)

# Floor/Ceiling
fig3 = create_floor_ceiling_chart(df)
st.plotly_chart(fig3)
```

### Running Simulations

```python
from services.simulations import run_player_simulations, calculate_boom_probability

# Simulate player
sims = run_player_simulations(mean=18.5, std=6.2, n_simulations=10000)

# Calculate boom probability
boom_prob = calculate_boom_probability(sims, salary=8500, boom_multiplier=4.0)
```

---

## Best Practices

### 1. **Keep Business Logic Pure**
```python
# ❌ Bad - mixes Streamlit with logic
def calculate_roi(df):
    st.write("Calculating ROI...")
    return df['profit'] / df['cost']

# ✅ Good - pure function
def calculate_roi(df):
    return df['profit'] / df['cost']
```

### 2. **Use Caching Appropriately**
```python
# Cache data loading
@st.cache_data(ttl=3600)
def load_expensive_data():
    return pd.read_csv("large_file.csv")

# Don't cache UI rendering
def render_dashboard():  # No @st.cache
    st.title("Dashboard")
```

### 3. **Leverage Imports**
```python
# Import what you need
from components.charts import create_ownership_scatter
from data.data_loader import load_roo_projections
from utils.constants import POSITIONS

# Not entire packages
# from components import *  # ❌
```

### 4. **Document Public Functions**
```python
def run_monte_carlo(n_simulations: int = 10000) -> np.ndarray:
    """
    Run Monte Carlo simulation
    
    Args:
        n_simulations: Number of iterations
        
    Returns:
        Array of simulated values
    """
    return np.random.normal(0, 1, n_simulations)
```

---

## Troubleshooting

### Import Errors
```python
# If you see "ModuleNotFoundError: No module named 'utils'"
# Make sure you're running from the correct directory:
cd c:\Users\schne\.vscode\.venv\dfsdude-tools
streamlit run app.py
```

### Page Not Showing
- Pages must be in `pages/` directory
- Filename must start with number: `1_Page.py`
- Restart Streamlit if page added while running

### Caching Issues
```python
# Clear cache in Streamlit
st.cache_data.clear()

# Or from terminal
streamlit cache clear
```

---

## Performance Tips

1. **Cache Data Loading**
   - Use `@st.cache_data` on all CSV loaders
   - Set appropriate TTL (time-to-live)

2. **Lazy Load Large Data**
   - Only load data when needed
   - Use tabs/expanders for optional content

3. **Optimize Charts**
   - Limit data points for scatter plots
   - Use sampling for large datasets

4. **Session State**
   - Store computation results in `st.session_state`
   - Avoid recomputing on every rerun

---

**Last Updated**: December 2, 2025  
**Version**: 2.0 (Modular Architecture)
