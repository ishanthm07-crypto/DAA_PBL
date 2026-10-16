"""RouteLab algorithm layer: pure functions, no web code.
Python port of algo.js (Dijkstra, Floyd-Warshall, Kruskal, Activity Selection,
Fractional Knapsack, 0/1 Knapsack) plus the independent verification helpers."""
from math import inf


def build_graph(stops, edges):
    idx = {s["id"]: i for i, s in enumerate(stops)}
    adj = [[] for _ in stops]
    for a, b, w in edges:
        adj[idx[a]].append((idx[b], w))
        adj[idx[b]].append((idx[a], w))
    return {"idx": idx, "adj": adj, "n": len(stops)}


def dijkstra(G, src):
    """Array version, O(V^2). Returns dist, prev and the order stops were finalised."""
    n = G["n"]
    dist, prev, done, order = [inf] * n, [-1] * n, [False] * n, []
    dist[src] = 0
    for _ in range(n):
        u = -1
        for i in range(n):
            if not done[i] and (u < 0 or dist[i] < dist[u]):
                u = i
        if u < 0 or dist[u] == inf:
            break
        done[u] = True
        order.append({"u": u, "d": dist[u], "via": prev[u]})
        for v, w in G["adj"][u]:
            if not done[v] and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u
    return {"dist": dist, "prev": prev, "order": order}


def path_to(prev, src, dst):
    p, v = [], dst
    while v != -1:
        p.append(v)
        if v == src:
            break
        v = prev[v]
    p.reverse()
    return p if p and p[0] == src else []


def floyd(G, edges):
    """Floyd-Warshall, O(V^3)."""
    n = G["n"]
    D = [[0 if i == j else inf for j in range(n)] for i in range(n)]
    for a, b, w in edges:
        i, j = G["idx"][a], G["idx"][b]
        D[i][j] = min(D[i][j], w)
        D[j][i] = min(D[j][i], w)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if D[i][k] + D[k][j] < D[i][j]:
                    D[i][j] = D[i][k] + D[k][j]
    return D


def kruskal(G, edges):
    """Kruskal with disjoint-set union, O(E log E). Returns every edge with its decision."""
    parent = list(range(G["n"]))
    rank = [0] * G["n"]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        if a == b:
            return False
        if rank[a] < rank[b]:
            a, b = b, a
        parent[b] = a
        if rank[a] == rank[b]:
            rank[a] += 1
        return True

    ordered = sorted(({"a": e[0], "b": e[1], "w": e[2], "i": i} for i, e in enumerate(edges)),
                     key=lambda e: (e["w"], e["i"]))
    steps, mst, total = [], [], 0
    for e in ordered:
        if len(mst) == G["n"] - 1:
            steps.append({**e, "status": "unused"})
            continue
        if union(G["idx"][e["a"]], G["idx"][e["b"]]):
            mst.append(e)
            total += e["w"]
            steps.append({**e, "status": "accepted"})
        else:
            steps.append({**e, "status": "rejected"})
    return {"steps": steps, "mst": mst, "total": total}


def activity_selection(trips):
    """Sort by finish time, keep each trip that starts at or after the last kept finish."""
    chosen, last = [], -inf
    for t in sorted(trips, key=lambda t: (t["end"], t["start"])):
        if t["start"] >= last:
            chosen.append(t)
            last = t["end"]
    return chosen


def fractional_knapsack(items, cap):
    """Highest value per seat first; the last group may be split."""
    ranked = sorted(({**x, "ratio": x["v"] / x["w"]} for x in items if x["w"] > 0),
                    key=lambda x: -x["ratio"])
    left, value, rows = cap, 0.0, []
    for x in ranked:
        take = min(x["w"], max(left, 0))
        left -= take
        value += x["ratio"] * take
        rows.append({**x, "take": take, "frac": take / x["w"]})
    return {"rows": rows, "value": value, "used": cap - max(left, 0), "left": max(left, 0)}


def knapsack01(items, cap):
    """0/1 knapsack, O(nW) table plus backtracking."""
    it = [x for x in items if x["w"] > 0]
    n = len(it)
    dp = [[0] * (cap + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w, v = it[i - 1]["w"], it[i - 1]["v"]
        for c in range(cap + 1):
            dp[i][c] = dp[i - 1][c]
            if w <= c and dp[i - 1][c - w] + v > dp[i][c]:
                dp[i][c] = dp[i - 1][c - w] + v
    picked, c = [], cap
    for i in range(n, 0, -1):
        if dp[i][c] != dp[i - 1][c]:
            picked.append(it[i - 1])
            c -= it[i - 1]["w"]
    picked.reverse()
    used = sum(x["w"] for x in picked)
    return {"picked": picked, "value": dp[n][cap], "used": used, "left": cap - used}


# ---- independent checks used by the Verification panel ----
def prim_weight(G):
    n = G["n"]
    in_t, key, total = [False] * n, [inf] * n, 0
    key[0] = 0
    for _ in range(n):
        u = -1
        for i in range(n):
            if not in_t[i] and (u < 0 or key[i] < key[u]):
                u = i
        if key[u] == inf:
            return inf
        in_t[u] = True
        total += key[u]
        for v, w in G["adj"][u]:
            if not in_t[v] and w < key[v]:
                key[v] = w
    return total


def max_compatible_dp(trips):
    s = sorted(trips, key=lambda t: t["end"])
    best, top = [1] * len(s), 0
    for i in range(len(s)):
        for j in range(i):
            if s[j]["end"] <= s[i]["start"]:
                best[i] = max(best[i], best[j] + 1)
        top = max(top, best[i])
    return top


def edge_sum(G, path):
    total = 0
    for a, b in zip(path, path[1:]):
        w = next((w for v, w in G["adj"][a] if v == b), None)
        if w is None:
            return float("nan")
        total += w
    return total
