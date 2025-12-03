"""
weekly_proe.py

Compute Weekly Pass Rate Over Expectation (PROE) using nflreadpy play-by-play data.

Requirements:
    pip install nflreadpy pandas numpy scikit-learn
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

import nflreadpy as nfl  # <- main change vs prior version


# ---------------------------------------------------
# 1. Load play-by-play data via nflreadpy
# ---------------------------------------------------

def load_pbp_from_nflreadpy(
    seasons: list[int] | int | None = None,
) -> pd.DataFrame:
    """
    Load play-by-play data using nflreadpy.

    Args:
        seasons: int or list of ints (e.g. 2022 or [2022, 2023]).
                 If None, nflreadpy.load_pbp() will use its default
                 behavior (usually current season).

    Returns:
        pandas DataFrame with nflfastR-style columns.
    """
    # nflreadpy returns a Polars DataFrame by default
    if seasons is None:
        pbp_pl = nfl.load_pbp()
    else:
        pbp_pl = nfl.load_pbp(seasons=seasons)

    # Convert to pandas for the rest of the pipeline
    pbp_pd = pbp_pl.to_pandas()
    return pbp_pd


# ---------------------------------------------------
# 2. Filter to relevant offensive plays
# ---------------------------------------------------

def filter_offensive_plays(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only offensive plays where the offense had a real choice
    between run and pass. Exclude penalties, spikes, kneels, etc.

    Assumes nflverse/nflfastR-style columns:
      - pass, rush, down, ydstogo, yardline_100, qtr,
        half_seconds_remaining, score_differential, qb_spike, qb_kneel
    """
    df = df.copy()

    # Basic filters: keep only plays that are labeled pass or rush
    mask_play_type = (df["pass"].isin([0, 1])) & (df["rush"].isin([0, 1]))
    df = df[mask_play_type]

    # Remove spikes and kneel-downs if present
    if "qb_spike" in df.columns:
        df = df[df["qb_spike"] != 1]
    if "qb_kneel" in df.columns:
        df = df[df["qb_kneel"] != 1]

    # Remove plays with missing core context
    required_cols = [
        "season",
        "week",
        "posteam",
        "down",
        "ydstogo",
        "yardline_100",
        "qtr",
        "half_seconds_remaining",
        "score_differential",
    ]
    for col in required_cols:
        df = df[df[col].notnull()]

    # Ensure down is valid
    df = df[df["down"].isin([1, 2, 3, 4])]

    # Create binary "is_pass" target
    df["is_pass"] = (df["pass"] == 1).astype(int)

    return df


# ---------------------------------------------------
# 3. Feature engineering for Expected Pass Model
# ---------------------------------------------------

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add / transform features used in the pass probability model.
    """
    df = df.copy()

    # Log transform for yards to go (helps with skew)
    df["log_ydstogo"] = np.log(df["ydstogo"].clip(lower=1))

    # Red zone indicator
    df["is_red_zone"] = (df["yardline_100"] <= 20).astype(int)

    # Clip big leads/deficits
    df["score_diff_clipped"] = df["score_differential"].clip(-21, 21)

    # Time remaining in half (log)
    df["log_half_seconds_remaining"] = np.log(
        df["half_seconds_remaining"].clip(lower=1)
    )

    return df


def get_feature_matrix(df: pd.DataFrame):
    """
    Return feature matrix X and target y for model fitting / prediction.

    Modify feature_cols list if you want to tweak the model.
    """
    feature_cols = [
        "down",
        "log_ydstogo",
        "yardline_100",
        "is_red_zone",
        "score_diff_clipped",
        "log_half_seconds_remaining",
        "qtr",
    ]

    X = df[feature_cols].values
    y = df["is_pass"].values
    return X, y, feature_cols


# ---------------------------------------------------
# 4. Train Expected Pass Probability Model
# ---------------------------------------------------

def train_expected_pass_model(df: pd.DataFrame) -> Pipeline:
    """
    Train a logistic regression model to estimate probability of a pass
    given game context.
    Returns a sklearn Pipeline: StandardScaler + LogisticRegression.
    """
    df = add_features(df)
    X, y, feature_cols = get_feature_matrix(df)

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "logreg",
                LogisticRegression(
                    max_iter=1000,
                    solver="lbfgs",
                ),
            ),
        ]
    )

    model.fit(X, y)
    return model


# ---------------------------------------------------
# 5. Compute Expected Pass Probability for Each Play
# ---------------------------------------------------

def add_expected_pass_prob(df: pd.DataFrame, model: Pipeline) -> pd.DataFrame:
    """
    Given a fitted model, add an 'exp_pass_prob' column to the dataframe.
    """
    df = add_features(df)
    X, _, _ = get_feature_matrix(df)

    exp_pass_prob = model.predict_proba(X)[:, 1]
    df["exp_pass_prob"] = exp_pass_prob

    return df


# ---------------------------------------------------
# 6. Aggregate to Weekly Team PROE
# ---------------------------------------------------

def compute_weekly_proe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute weekly Pass Rate Over Expectation (PROE) for each team.
    PROE = Actual Pass Rate - Expected Pass Rate.
    """
    group_cols = ["season", "week", "posteam"]

    grouped = df.groupby(group_cols).agg(
        plays=("is_pass", "count"),
        actual_pass_plays=("is_pass", "sum"),
        expected_pass_prob=("exp_pass_prob", "mean"),
    )

    grouped["actual_pass_rate"] = grouped["actual_pass_plays"] / grouped["plays"]
    grouped["expected_pass_rate"] = grouped["expected_pass_prob"]

    grouped["proe"] = grouped["actual_pass_rate"] - grouped["expected_pass_rate"]

    grouped = grouped.reset_index()

    # Optional: filter out tiny samples (e.g., < 15 plays in a week)
    grouped = grouped[grouped["plays"] >= 15]

    return grouped


# ---------------------------------------------------
# 7. High-level helper from nflreadpy to Weekly PROE
# ---------------------------------------------------

def build_weekly_proe_from_nflreadpy(
    seasons: list[int] | int | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """
    High-level helper:
    1. Load PBP from nflreadpy
    2. Filter offensive plays
    3. Train expected pass model
    4. Add expected pass probabilities
    5. Aggregate to weekly PROE
    6. Optionally save to CSV

    Args:
        seasons: int or list of ints (e.g. 2022, or [2022, 2023]).
                 If None, uses nflreadpy.load_pbp() default.
        output_path: optional CSV path for saving the weekly PROE table.
    """
    # 1. Load via nflreadpy
    df = load_pbp_from_nflreadpy(seasons=seasons)

    # 2. Filter to relevant plays
    df = filter_offensive_plays(df)

    # 3. Train model on full filtered dataset
    model = train_expected_pass_model(df)

    # 4. Add expected pass probabilities
    df = add_expected_pass_prob(df, model)

    # 5. Compute weekly PROE
    weekly_proe = compute_weekly_proe(df)

    # 6. Save if requested
    if output_path is not None:
        weekly_proe.to_csv(output_path, index=False)

    return weekly_proe


# ---------------------------------------------------
# 8. Example usage
# ---------------------------------------------------

if __name__ == "__main__":
    # Example: compute weekly PROE for 2025 and write to CSV
    seasons = [2025]
    out_file = r"C:\Users\schne\Documents\DFS\2025\Dashboard\weekly_proe_2025.csv"

    weekly_proe_df = build_weekly_proe_from_nflreadpy(
        seasons=seasons,
        output_path=out_file,
    )

    print(weekly_proe_df.head())
    print(f"\nSaved weekly PROE to: {out_file}")
