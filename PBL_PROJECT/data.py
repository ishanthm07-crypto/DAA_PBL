"""Woxsen campus sample data (schematic, not to scale)."""
STOPS = [
    {"id": "MG", "name": "Main Gate", "short": "Main Gate", "x": 120, "y": 60, "lp": "r"},
    {"id": "AI", "name": "AI Research Centre", "short": "AI Research", "x": 150, "y": 190, "lp": "r"},
    {"id": "AR", "name": "School of Architecture", "short": "Architecture", "x": 400, "y": 170, "lp": "t"},
    {"id": "AB", "name": "Admin Block", "short": "Admin Block", "x": 200, "y": 310, "lp": "l"},
    {"id": "LW", "name": "School of Law", "short": "Law School", "x": 440, "y": 320, "lp": "t"},
    {"id": "LB", "name": "Library and Coffee & Co.", "short": "Library", "x": 240, "y": 450, "lp": "b"},
    {"id": "BE", "name": "Blue Ember Restaurant", "short": "Blue Ember", "x": 80, "y": 420, "lp": "t"},
    {"id": "T5", "name": "Tower 5", "short": "Tower 5", "x": 560, "y": 470, "lp": "t"},
    {"id": "T3", "name": "Tower 3", "short": "Tower 3", "x": 740, "y": 400, "lp": "t"},
    {"id": "T2", "name": "Tower 2", "short": "Tower 2", "x": 760, "y": 550, "lp": "b"},
    {"id": "OV", "name": "The Oval", "short": "The Oval", "x": 420, "y": 570, "lp": "b"},
    {"id": "SP", "name": "Sports Complex (Cricket Stadium)", "short": "Sports Complex", "x": 130, "y": 585, "lp": "b"},
]

# (from, to, minutes by shuttle)
EDGES = [
    ("MG", "AI", 3), ("AI", "AB", 2), ("AI", "AR", 4), ("AR", "LW", 2), ("AB", "LW", 3),
    ("AB", "LB", 2), ("AB", "BE", 3), ("LB", "BE", 2), ("LB", "OV", 4), ("LB", "T5", 5),
    ("LW", "T5", 4), ("LW", "T3", 5), ("T5", "T3", 3), ("T5", "T2", 4), ("T3", "T2", 2),
    ("T5", "OV", 3), ("OV", "SP", 5), ("LB", "SP", 6), ("BE", "SP", 5),
]

TURNAROUND = 4  # minutes of boarding and turnaround added to every trip

# n = passengers waiting, w = average wait in minutes
DEFAULT_DEMAND = {
    "MG": {"n": 14, "w": 4}, "AI": {"n": 6, "w": 3}, "AR": {"n": 9, "w": 5}, "AB": {"n": 18, "w": 6},
    "LW": {"n": 11, "w": 4}, "LB": {"n": 22, "w": 7}, "BE": {"n": 8, "w": 3}, "T5": {"n": 26, "w": 9},
    "T3": {"n": 17, "w": 8}, "T2": {"n": 15, "w": 8}, "OV": {"n": 12, "w": 5}, "SP": {"n": 10, "w": 6},
}

DEFAULT_FLEET = [
    {"id": "SH-01", "driver": "Ravi K.", "status": "Active", "loc": "LB", "route": "Main Gate to Tower 5", "occ": 28, "cap": 40},
    {"id": "SH-02", "driver": "Meera S.", "status": "Available", "loc": "AB", "route": "Idle at Admin Block", "occ": 0, "cap": 40},
]

# start times in minutes after midnight
DEFAULT_TRIPS = [
    {"id": 1, "start": 480, "from": "MG", "to": "T5"}, {"id": 2, "start": 485, "from": "MG", "to": "AB"},
    {"id": 3, "start": 492, "from": "AB", "to": "LB"}, {"id": 4, "start": 500, "from": "LB", "to": "T3"},
    {"id": 5, "start": 502, "from": "AI", "to": "OV"}, {"id": 6, "start": 510, "from": "T5", "to": "SP"},
    {"id": 7, "start": 515, "from": "BE", "to": "T2"}, {"id": 8, "start": 525, "from": "AR", "to": "OV"},
    {"id": 9, "start": 530, "from": "OV", "to": "MG"}, {"id": 10, "start": 540, "from": "LW", "to": "SP"},
]

USERS = {
    "passenger": {"email": "student@woxsen.edu.in", "password": "demo123"},
    "admin": {"email": "admin@woxsen.edu.in", "password": "admin123"},
}
