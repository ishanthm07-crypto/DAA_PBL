"""Checks the Python port against the results quoted in the DAA presentation."""
from algo import *
from data import *

G = build_graph(STOPS, EDGES)
FW = floyd(G, EDGES)
ids = [s["id"] for s in STOPS]
ok = True
def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("PASS  " if cond else "FAIL  ") + name, detail)

r = dijkstra(G, G["idx"]["MG"])
p = [ids[i] for i in path_to(r["prev"], 0, G["idx"]["T5"])]
check("Dijkstra Main Gate -> Tower 5 = 12 min", r["dist"][G["idx"]["T5"]] == 12, p)
check("Dijkstra first five finalised: MG, AI, AB, AR, LB",
      [ids[o["u"]] for o in r["order"][:5]] == ["MG", "AI", "AB", "AR", "LB"],
      [(ids[o["u"]], o["d"]) for o in r["order"][:5]])
mism = sum(dijkstra(G, s)["dist"][t] != FW[s][t] for s in range(G["n"]) for t in range(G["n"]))
check("Dijkstra agrees with Floyd-Warshall on 144 pairs", mism == 0, f"{mism} differences")
bad = sum(edge_sum(G, path_to((d := dijkstra(G, s))["prev"], s, t)) != d["dist"][t]
          for s in range(G["n"]) for t in range(G["n"]))
check("Route time equals sum of road weights", bad == 0)
k = kruskal(G, EDGES)
check("Kruskal: 11 edges, weight 31, equals Prim", len(k["mst"]) == 11 and k["total"] == 31 == prim_weight(G),
      (len(k["mst"]), k["total"], prim_weight(G)))
trips = [{**t, "end": t["start"] + FW[G["idx"][t["from"]]][G["idx"][t["to"]]] + TURNAROUND} for t in DEFAULT_TRIPS]
sel = activity_selection(trips)
check("Activity selection: 4 of 10, matches DP maximum", len(sel) == 4 == max_compatible_dp(trips), len(sel))
items = [{"id": s["id"], "name": s["short"], "w": DEFAULT_DEMAND[s["id"]]["n"],
          "v": DEFAULT_DEMAND[s["id"]]["n"] * DEFAULT_DEMAND[s["id"]]["w"]} for s in STOPS]
z, f = knapsack01(items, 40), fractional_knapsack(items, 40)
check("0/1 knapsack: 38/40 seats, value 294", z["used"] == 38 and z["value"] == 294, (z["used"], z["value"]))
check("Fractional knapsack value 346 (upper bound)", round(f["value"]) == 346, round(f["value"], 1))
check("0/1 never beats fractional", z["value"] <= f["value"] + 1e-9)
print("\nALL PASS" if ok else "\nSOME FAILED")
raise SystemExit(0 if ok else 1)
