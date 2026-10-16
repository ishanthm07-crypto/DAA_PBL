# RouteLab (Python edition) - Woxsen Campus Shuttle Routing and Capacity Scheduling

Python port of the RouteLab web app. Everything is computed in Python; the
only browser-side script is the shuttle animation on the passenger page.

## Run
```
pip install flask
python app.py          # open http://127.0.0.1:5000
python test_algo.py    # checks the algorithms against the numbers in the DAA deck
```
Demo logins: `student@woxsen.edu.in / demo123` (passenger), `admin@woxsen.edu.in / admin123` (administrator).

## Files
| File | Purpose |
|---|---|
| algo.py | Dijkstra, Floyd-Warshall, Kruskal, Activity Selection, Fractional and 0/1 Knapsack, Prim and DP verifiers |
| data.py | 12 stops, 19 roads, demand, fleet, trips, demo users |
| app.py | Flask app: login, passenger pages, admin pages, live verification |
| static/style.css | Your original stylesheet (plus 6 small lines for links) |
| test_algo.py | 9 checks: 12 min route, MST 31 / 11 roads, 4 of 10 trips, 38/40 seats, 294 vs 346 |

State (edited demand, capacity, trips) is kept in memory and resets when the server restarts.
