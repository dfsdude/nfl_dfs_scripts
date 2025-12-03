✅ Example Directory & File Structure for a Modular Streamlit App
my_streamlit_app/
│
├── app.py
│
├── pages/
│   ├── 1_🏠_Home.py
│   ├── 2_📊_Analytics.py
│   ├── 3_🧮_Simulations.py
│   └── 4_⚙️_Settings.py
│
├── components/
│   ├── __init__.py
│   ├── layouts.py              # Reusable containers, columns, card layouts
│   ├── widgets.py              # Custom Streamlit widgets
│   ├── charts.py               # Plotly/Matplotlib chart builders
│   └── tables.py               # Reusable table builders
│
├── data/
│   ├── __init__.py
│   ├── data_loader.py          # Functions to load local or remote data
│   ├── caching.py              # Other caching utilities
│   └── transformations.py      # Aggregations, helpers, feature engineering
│
├── services/
│   ├── __init__.py
│   ├── api_client.py           # Calls to external APIs
│   ├── ml_models.py            # ML training / inference
│   └── simulations.py          # Monte Carlo logic, proprietary model code
│
├── utils/
│   ├── __init__.py
│   ├── config.py               # App-wide config variables
│   ├── logger.py               # Custom logger
│   ├── constants.py            # Centralized constants (teams, colors, etc.)
│   └── helpers.py              # Generic helper functions
│
├── assets/
│   ├── logo.png
│   ├── styles.css
│   └── example_data.csv
│
├── requirements.txt
└── README.md

🧩 Explanation of the major pieces
app.py

Your main entry point.
Controls navigation, loads session state, sets up the theme, etc.

Example:

import streamlit as st
from utils.config import init_config

def main():
    init_config()
    st.sidebar.title("Navigation")
    st.sidebar.switch_page("pages/1_🏠_Home.py")

if __name__ == "__main__":
    main()

pages/ directory

Streamlit automatically shows these as separate pages in the sidebar.

The number prefix controls ordering:

1_... loads first

2_... next

Emojis allow clean page grouping

Example 2_📊_Analytics.py:

import streamlit as st
from components.charts import line_chart
from data.data_loader import load_weekly_data

st.title("Analytics Dashboard")

df = load_weekly_data()

st.subheader("Weekly Trends")
st.plotly_chart(line_chart(df))

🧱 components/ — reusable UI blocks

👑 This is what makes your app modular.
Everything from cards → tables → custom widgets

layouts.py

import streamlit as st

def centered_card(title, body):
    with st.container():
        st.markdown(f"### {title}")
        st.write(body)


charts.py

import plotly.express as px

def line_chart(df):
    return px.line(df, x="week", y="value")

📦 data/ — loading & transforming data

Your ETL and caching layer.

data_loader.py

import pandas as pd
import streamlit as st

@st.cache_data
def load_weekly_data():
    return pd.read_csv("assets/example_data.csv")

⚙️ services/ — business logic / ML / simulation

Pure logic.
Zero Streamlit imports → makes testing easier.

simulations.py

import numpy as np

def run_monte_carlo(n=1000):
    return np.random.normal(loc=50, scale=10, size=n)

🛠 utils/ — cross-cutting helpers

config.py

import streamlit as st

def init_config():
    st.set_page_config(
        page_title="DFS Simulator",
        layout="wide",
        page_icon="🏈",
    )


constants.py

TEAMS = ["DAL", "PHI", "SF", "KC"]

🎨 assets/ — images, CSS, CSVs, etc.

Drop theme overrides, logos, static example data here.

Optional CSS injection:

st.markdown("<style>" + open("assets/styles.css").read() + "</style>",
             unsafe_allow_html=True)

📌 Summary

This structure gives you:

✔ Highly modular code
✔ Clear separation of UI vs. logic
✔ Easy testing
✔ Easy to scale to many pages
✔ Clean folder breakdown as your DFS tools grow