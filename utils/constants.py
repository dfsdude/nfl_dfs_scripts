"""
Constants module for DFS Tools Suite
Centralized storage for NFL teams, positions, and other constants
"""

# NFL Team abbreviation to full name mapping
TEAM_MAPPING = {
    'ARI': 'Cardinals', 'ATL': 'Falcons', 'BAL': 'Ravens', 'BUF': 'Bills',
    'CAR': 'Panthers', 'CHI': 'Bears', 'CIN': 'Bengals', 'CLE': 'Browns',
    'DAL': 'Cowboys', 'DEN': 'Broncos', 'DET': 'Lions', 'GB': 'Packers',
    'HOU': 'Texans', 'IND': 'Colts', 'JAX': 'Jaguars', 'KC': 'Chiefs',
    'LAC': 'Chargers', 'LAR': 'Rams', 'LV': 'Raiders', 'MIA': 'Dolphins',
    'MIN': 'Vikings', 'NE': 'Patriots', 'NO': 'Saints', 'NYG': 'Giants',
    'NYJ': 'Jets', 'PHI': 'Eagles', 'PIT': 'Steelers', 'SEA': 'Seahawks',
    'SF': '49ers', 'TB': 'Buccaneers', 'TEN': 'Titans', 'WAS': 'Commanders'
}

# Reverse mapping (full name to abbreviation)
TEAM_MAPPING_REVERSE = {v: k for k, v in TEAM_MAPPING.items()}

# DFS positions
POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST']

# Roster construction (DraftKings)
ROSTER_CONSTRUCTION = {
    'QB': 1,
    'RB': 2,
    'WR': 3,
    'TE': 1,
    'FLEX': 1,  # RB/WR/TE
    'DST': 1
}

# Salary cap
SALARY_CAP = 50000

# Colors for charts
POSITION_COLORS = {
    'QB': '#1f77b4',
    'RB': '#ff7f0e',
    'WR': '#2ca02c',
    'TE': '#d62728',
    'DST': '#9467bd'
}

# Boom thresholds
BOOM_THRESHOLD = 4.0  # 4x salary multiplier
