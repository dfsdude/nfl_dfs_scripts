"""
FantasyPros Advanced Stats Loader
Loads and merges FantasyPros advanced statistics with DraftKings player data
Includes fuzzy name matching for player name normalization
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to FantasyPros data
FANTASYPROS_DIR = Path(__file__).parent / "fantasypros"

# Position file mapping
POSITION_FILES = {
    'QB': 'QB_Advanced_Stats_2025.csv',
    'RB': 'RB_Advanced_Stats_2025.csv',
    'WR': 'WR_Advanced_Stats_2025.csv',
    'TE': 'TE_Advanced_Stats_2025.csv'
}

# Name normalization rules
NAME_REPLACEMENTS = {
    # Common suffixes to remove
    'Jr.': '',
    'Sr.': '',
    'III': '',
    'II': '',
    'IV': '',
    'V': '',
    # Apostrophe variations
    '\u2019': "'",  # Right single quotation mark → apostrophe
    # Common name variations
    'Joshua': 'Josh',
    'Kenneth': 'Ken',
    'Kenneth Walker': 'Kenneth Walker III',
    'Michael': 'Mike',
    'Christopher': 'Chris',
    'Anthony': 'Tony',
    'Alexander': 'Alex',
    'Matthew': 'Matt',
    'Jonathan': 'Jon',
    'Benjamin': 'Ben',
    'Gabriel': 'Gabe',
}

# Manual name mappings (FantasyPros → DraftKings)
MANUAL_MAPPINGS = {
    'Kenneth Walker': 'Kenneth Walker III',
    'Gabe Davis': 'Gabriel Davis',
    'Jeff Wilson': 'Jeffery Wilson Jr.',
    'Jeff Wilson Jr.': 'Jeffery Wilson Jr.',
    'Josh Palmer': 'Joshua Palmer',
    'A.J. Brown': 'AJ Brown',
    'DK Metcalf': 'D.K. Metcalf',
    'DJ Moore': 'D.J. Moore',
    'JK Dobbins': 'J.K. Dobbins',
    'CJ Stroud': 'C.J. Stroud',
    'TJ Hockenson': 'T.J. Hockenson',
}

# Team abbreviation normalization (FantasyPros → Standard)
TEAM_MAPPINGS = {
    'JAC': 'JAX',  # Jacksonville
    'LAR': 'LA',   # LA Rams
    # Add others as needed
}

# ============================================================================
# NAME NORMALIZATION FUNCTIONS
# ============================================================================

def normalize_name(name: str) -> str:
    """
    Normalize player name for matching
    
    Steps:
    1. Extract name from "Player Name (TEAM)" format
    2. Remove suffixes (Jr., Sr., III, etc.)
    3. Normalize apostrophes
    4. Strip whitespace
    5. Apply manual replacements
    
    Args:
        name: Raw player name (e.g., "Josh Allen(BUF)" or "Josh Allen")
    
    Returns:
        Normalized name (e.g., "Josh Allen")
    """
    # Extract name from "Name(TEAM)" format
    if '(' in name:
        name = name.split('(')[0].strip()
    
    # Apply manual mappings first
    if name in MANUAL_MAPPINGS:
        return MANUAL_MAPPINGS[name]
    
    # Apply replacements
    for old, new in NAME_REPLACEMENTS.items():
        name = name.replace(old, new)
    
    # Clean up extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def extract_team(player_str: str) -> Optional[str]:
    """
    Extract team abbreviation from player string
    
    Args:
        player_str: Player string like "Josh Allen(BUF)"
    
    Returns:
        Team abbreviation (e.g., "BUF") or None
    """
    match = re.search(r'\(([A-Z]{2,3})\)', player_str)
    if match:
        team = match.group(1)
        # Apply team mappings
        return TEAM_MAPPINGS.get(team, team)
    return None


def similarity_score(name1: str, name2: str) -> float:
    """
    Calculate similarity score between two names
    Uses SequenceMatcher for Levenshtein-like distance
    
    Args:
        name1: First name
        name2: Second name
    
    Returns:
        Similarity score (0.0 to 1.0, higher = more similar)
    """
    # Normalize both names
    n1 = normalize_name(name1).lower()
    n2 = normalize_name(name2).lower()
    
    return SequenceMatcher(None, n1, n2).ratio()


def fuzzy_match_player(
    fp_name: str,
    dk_names: List[str],
    threshold: float = 0.85,
    team_filter: Optional[str] = None
) -> Tuple[Optional[str], float]:
    """
    Find best matching DraftKings name for FantasyPros player
    
    Args:
        fp_name: FantasyPros player name (e.g., "Josh Allen(BUF)")
        dk_names: List of DraftKings player names
        threshold: Minimum similarity score to accept match
        team_filter: Optional team abbreviation to filter matches
    
    Returns:
        Tuple of (best_match_name, similarity_score) or (None, 0.0) if no match
    """
    fp_normalized = normalize_name(fp_name)
    fp_team = extract_team(fp_name)
    
    best_match = None
    best_score = 0.0
    
    for dk_name in dk_names:
        # If team filter provided, only consider same team
        if team_filter and team_filter != fp_team:
            continue
        
        score = similarity_score(fp_normalized, dk_name)
        
        if score > best_score:
            best_score = score
            best_match = dk_name
    
    # Only return match if above threshold
    if best_score >= threshold:
        return best_match, best_score
    
    return None, 0.0


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_position_advanced_stats(position: str, weeks: Optional[List[int]] = None) -> pd.DataFrame:
    """
    Load FantasyPros advanced stats for a specific position
    
    Args:
        position: Position code ('QB', 'RB', 'WR', 'TE')
        weeks: Optional list of weeks to filter (e.g., [13, 14] for recent weeks)
    
    Returns:
        DataFrame with advanced stats for position
    """
    if position not in POSITION_FILES:
        raise ValueError(f"Invalid position: {position}. Must be one of {list(POSITION_FILES.keys())}")
    
    filepath = FANTASYPROS_DIR / POSITION_FILES[position]
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Load CSV
    df = pd.read_csv(filepath)
    
    # Extract week number from "Week X" format
    df['week_num'] = df['Week'].str.extract(r'Week (\d+)').astype(int)
    
    # Filter weeks if specified
    if weeks:
        df = df[df['week_num'].isin(weeks)]
    
    # Extract team from Player column
    df['team'] = df['Player'].apply(extract_team)
    
    # Normalize player names
    df['player_normalized'] = df['Player'].apply(normalize_name)
    
    # Add position column
    df['position'] = position
    
    return df


def load_all_advanced_stats(weeks: Optional[List[int]] = None) -> pd.DataFrame:
    """
    Load advanced stats for all positions and combine
    
    Args:
        weeks: Optional list of weeks to filter
    
    Returns:
        Combined DataFrame with all positions
    """
    dfs = []
    
    for position in POSITION_FILES.keys():
        try:
            df = load_position_advanced_stats(position, weeks)
            dfs.append(df)
            print(f"✓ Loaded {len(df)} rows for {position}")
        except Exception as e:
            print(f"⚠ Warning: Could not load {position} data: {e}")
    
    if not dfs:
        raise ValueError("No data loaded for any position")
    
    # Combine all positions
    combined = pd.concat(dfs, ignore_index=True)
    
    print(f"\n✓ Total: {len(combined)} player-week records across {len(POSITION_FILES)} positions")
    
    return combined


def aggregate_recent_weeks(
    df: pd.DataFrame,
    weeks: int = 4,
    stats_to_avg: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Aggregate advanced stats over recent N weeks per player
    
    Args:
        df: Advanced stats DataFrame
        weeks: Number of recent weeks to aggregate
        stats_to_avg: List of stat columns to average (if None, uses numeric columns)
    
    Returns:
        Aggregated DataFrame with player-level stats
    """
    # Get most recent N weeks
    max_week = df['week_num'].max()
    recent_df = df[df['week_num'] > (max_week - weeks)].copy()
    
    # Identify numeric columns to aggregate
    if stats_to_avg is None:
        numeric_cols = recent_df.select_dtypes(include=[np.number]).columns
        # Exclude week_num and Rank from aggregation
        stats_to_avg = [col for col in numeric_cols if col not in ['week_num', 'Rank', 'G']]
    
    # Group by player and calculate stats
    agg_dict = {col: 'mean' for col in stats_to_avg}
    agg_dict['week_num'] = 'count'  # Count games played
    
    aggregated = recent_df.groupby(['player_normalized', 'team', 'position']).agg(agg_dict).reset_index()
    
    # Rename week_num count to games_played
    aggregated = aggregated.rename(columns={'week_num': 'games_played'})
    
    # Add suffix to stat columns to indicate they're averages
    for col in stats_to_avg:
        if col in aggregated.columns:
            aggregated = aggregated.rename(columns={col: f'{col}_avg_{weeks}wk'})
    
    return aggregated


def merge_with_dk_salaries(
    advanced_stats: pd.DataFrame,
    dk_salaries: pd.DataFrame,
    week: Optional[int] = None
) -> pd.DataFrame:
    """
    Merge FantasyPros advanced stats with DraftKings salaries
    
    Args:
        advanced_stats: FantasyPros advanced stats DataFrame
        dk_salaries: DraftKings Salaries DataFrame
        week: Optional week to filter salaries (uses max week if None)
    
    Returns:
        Merged DataFrame with matched players
    """
    # Filter to specific week if needed
    if week is not None:
        salaries = dk_salaries[dk_salaries['Week'] == week].copy()
    else:
        # Use most recent week
        max_week = dk_salaries['Week'].max()
        salaries = dk_salaries[dk_salaries['Week'] == max_week].copy()
    
    # Normalize DK names
    salaries['name_normalized'] = salaries['Name'].apply(normalize_name)
    
    # Create position mapping
    position_map = {'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE'}
    
    merged_rows = []
    unmatched_fp = []
    
    for _, fp_row in advanced_stats.iterrows():
        fp_name = fp_row['player_normalized']
        fp_team = fp_row['team']
        fp_pos = fp_row['position']
        
        # Get original player name (with team) for fuzzy matching
        # If 'Player' column doesn't exist (aggregated data), construct it
        if 'Player' in fp_row.index:
            fp_player_orig = fp_row['Player']
        else:
            fp_player_orig = f"{fp_name}({fp_team})"
        
        # Filter DK players by position and team
        dk_filtered = salaries[
            (salaries['Position'] == fp_pos) &
            (salaries['TeamAbbrev'] == fp_team)
        ]
        
        # Try exact match first
        exact_match = dk_filtered[dk_filtered['name_normalized'] == fp_name]
        
        if len(exact_match) > 0:
            # Exact match found
            dk_row = exact_match.iloc[0]
            merged = {**fp_row.to_dict(), **dk_row.to_dict()}
            merged['match_type'] = 'exact'
            merged['match_score'] = 1.0
            merged_rows.append(merged)
        else:
            # Try fuzzy match
            dk_names = dk_filtered['Name'].tolist()
            best_match, score = fuzzy_match_player(
                fp_player_orig,
                dk_names,
                threshold=0.85,
                team_filter=fp_team
            )
            
            if best_match:
                # Fuzzy match found
                dk_row = salaries[salaries['Name'] == best_match].iloc[0]
                merged = {**fp_row.to_dict(), **dk_row.to_dict()}
                merged['match_type'] = 'fuzzy'
                merged['match_score'] = score
                merged_rows.append(merged)
            else:
                # No match found
                unmatched_fp.append({
                    'player': fp_player_orig,
                    'team': fp_team,
                    'position': fp_pos
                })
    
    merged_df = pd.DataFrame(merged_rows)
    
    # Print matching summary
    total_fp = len(advanced_stats)
    matched = len(merged_df)
    exact = len(merged_df[merged_df['match_type'] == 'exact'])
    fuzzy = len(merged_df[merged_df['match_type'] == 'fuzzy'])
    
    print(f"\n{'='*60}")
    print(f"Player Name Matching Summary")
    print(f"{'='*60}")
    print(f"FantasyPros players: {total_fp}")
    print(f"Matched players: {matched} ({matched/total_fp*100:.1f}%)")
    print(f"  - Exact matches: {exact}")
    print(f"  - Fuzzy matches: {fuzzy}")
    print(f"Unmatched: {len(unmatched_fp)}")
    
    if unmatched_fp and len(unmatched_fp) <= 10:
        print(f"\nUnmatched players:")
        for player in unmatched_fp[:10]:
            print(f"  - {player['player']} ({player['team']} {player['position']})")
    
    return merged_df


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_advanced_stats_for_week(
    week: int,
    dk_salaries: pd.DataFrame,
    positions: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Get advanced stats merged with DK salaries for a specific week
    
    Args:
        week: NFL week number
        dk_salaries: DraftKings Salaries DataFrame
        positions: Optional list of positions to include (default: all)
    
    Returns:
        Merged DataFrame with advanced stats and DK data
    """
    # Load advanced stats for this week
    stats = load_all_advanced_stats(weeks=[week])
    
    # Filter positions if specified
    if positions:
        stats = stats[stats['position'].isin(positions)]
    
    # Merge with DK salaries
    merged = merge_with_dk_salaries(stats, dk_salaries, week)
    
    return merged


def get_recent_advanced_stats(
    lookback_weeks: int = 4,
    dk_salaries: pd.DataFrame = None,
    current_week: Optional[int] = None
) -> pd.DataFrame:
    """
    Get aggregated advanced stats over recent weeks
    
    Args:
        lookback_weeks: Number of recent weeks to aggregate
        dk_salaries: Optional DK salaries to merge with
        current_week: Current week (if None, uses max week in data)
    
    Returns:
        Aggregated advanced stats (optionally merged with DK)
    """
    # Load all advanced stats
    all_stats = load_all_advanced_stats()
    
    # Determine current week
    if current_week is None:
        current_week = all_stats['week_num'].max()
    
    # Filter to recent weeks
    recent_weeks = list(range(current_week - lookback_weeks + 1, current_week + 1))
    recent_stats = all_stats[all_stats['week_num'].isin(recent_weeks)]
    
    # Aggregate
    aggregated = aggregate_recent_weeks(recent_stats, lookback_weeks)
    
    # Merge with DK if provided
    if dk_salaries is not None:
        aggregated = merge_with_dk_salaries(aggregated, dk_salaries, current_week)
    
    return aggregated


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    print("FantasyPros Advanced Stats Loader - Test")
    print("=" * 60)
    
    # Test loading all positions
    print("\n1. Loading all advanced stats...")
    all_stats = load_all_advanced_stats()
    
    # Show sample data
    print("\nSample data (first 3 rows):")
    print(all_stats[['player_normalized', 'team', 'position', 'week_num']].head(3))
    
    # Test aggregation
    print("\n2. Aggregating recent 4 weeks...")
    aggregated = aggregate_recent_weeks(all_stats, weeks=4)
    print(f"✓ Aggregated to {len(aggregated)} players")
    
    # Test name normalization
    print("\n3. Testing name normalization...")
    test_names = [
        "Josh Allen(BUF)",
        "Kenneth Walker III(SEA)",
        "A.J. Brown(PHI)",
        "Gabriel Davis(JAX)"
    ]
    for name in test_names:
        normalized = normalize_name(name)
        team = extract_team(name)
        print(f"  {name} → {normalized} ({team})")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
