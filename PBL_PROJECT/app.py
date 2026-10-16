"""RouteLab (Python edition): Woxsen campus shuttle routing and capacity scheduling.

Flask serves server-rendered pages. Every algorithm result is computed in Python
(algo.py). The only browser-side script is the small shuttle animation on the
passenger page. Run:  python app.py   then open http://127.0.0.1:5000
"""
import copy
import json
import math
import time
from html import escape

from flask import Flask, Response, redirect, request, session, url_for

from algo import (activity_selection, build_graph, dijkstra, edge_sum, floyd, fractional_knapsack,
                  knapsack01, kruskal, max_compatible_dp, path_to, prim_weight)
from data import (DEFAULT_DEMAND, DEFAULT_FLEET, DEFAULT_TRIPS, EDGES, STOPS, TURNAROUND, USERS)

app = Flask(__name__)
app.secret_key = "routelab-demo-key"

G = build_graph(STOPS, EDGES)
FW = floyd(G, EDGES)

# ------------------------------------------------------------------ state (in memory, demo)
S = {
    "demand": copy.deepcopy(DEFAULT_DEMAND),
    "fleet": copy.deepcopy(DEFAULT_FLEET),
    "trips": copy.deepcopy(DEFAULT_TRIPS),
    "next_trip": 11,
    "alloc": "SH-01",
    "bench": None,
}

# ------------------------------------------------------------------ helpers
esc = lambda s: escape(str(s), quote=True)
jsround = lambda x: math.floor(x + 0.5)
sid = lambda i: STOPS[G["idx"][i]]
nm = lambda i: sid(i)["name"]
short = lambda i: sid(i)["short"]
dist = lambda a, b: FW[G["idx"][a]][G["idx"][b]]
trip_end = lambda t: t["start"] + dist(t["from"], t["to"]) + TURNAROUND
fmt_t = lambda m: f"{int(m // 60):02d}:{int(jsround(m % 60)):02d}"
fleet_by = lambda i: next(f for f in S["fleet"] if f["id"] == i)
road = lambda a, b: next(w for x, y, w in EDGES if (x, y) == (a, b) or (y, x) == (a, b))


def parse_t(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def clamp_int(v, lo, hi):
    try:
        v = jsround(float(v))
    except (TypeError, ValueError):
        v = 0
    return max(lo, min(hi, v))


def route(src, dst):
    r = dijkstra(G, G["idx"][src])
    path = [STOPS[i]["id"] for i in path_to(r["prev"], G["idx"][src], G["idx"][dst])]
    return {"path": path, "time": r["dist"][G["idx"][dst]]}


MST = lambda: kruskal(G, EDGES)
trips_with_end = lambda: [{**t, "end": trip_end(t)} for t in S["trips"]]


def demand_items():
    return [{"id": s["id"], "name": s["short"], "w": S["demand"][s["id"]]["n"],
             "v": S["demand"][s["id"]]["n"] * S["demand"][s["id"]]["w"]} for s in STOPS]


def avg_route():
    pairs = [FW[i][j] for i in range(G["n"]) for j in range(i + 1, G["n"])]
    return sum(pairs) / len(pairs)


IC = {
    "route": '<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h6a3.5 3.5 0 0 0 0-7h-4a3.5 3.5 0 0 1 0-7h6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "grid": '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    "net": '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="8" r="2"/><circle cx="8" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6l8 2M7 8l1 8M10 18h6M18 10v6"/>',
    "bus": '<rect x="4" y="4" width="16" height="13" rx="2"/><path d="M4 11h16M7 20v-3M17 20v-3"/>',
    "flask": '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/>',
    "cal": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    "out": '<path d="M9 4H5v16h4M16 8l4 4-4 4M20 12H9"/>',
    "swap": '<path d="M7 4L4 7l3 3M4 7h13M17 20l3-3-3-3M20 17H7"/>',
    "play": '<path d="M7 5v14l12-7z"/>',
    "reset": '<path d="M4 12a8 8 0 1 0 3-6.2M4 4v4h4"/>',
}
icon = lambda n: ('<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                  'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + IC[n] + "</svg>")


def qs(**kw):
    from urllib.parse import urlencode
    return urlencode({k: v for k, v in kw.items() if v is not None})


# ------------------------------------------------------------------ schematic map
def map_svg(path=(), mst=(), src=None, dst=None, pick=None, demand=False, bus=None,
            label="Schematic map of Woxsen campus stops and shuttle roads"):
    on_path = set(path)
    pe = {"-".join(sorted([path[i], path[i + 1]])) for i in range(len(path) - 1)}
    me = {"-".join(sorted([e["a"], e["b"]])) for e in mst}
    max_d = max([1] + [S["demand"][s["id"]]["n"] for s in STOPS])
    h = [f'<svg class="map" viewBox="0 0 960 640" role="img" aria-label="{esc(label)}">',
         '<text x="920" y="40" class="wlab" style="font-size:12px">N &#8593;</text>']
    for a, b, w in EDGES:
        A, B, k = sid(a), sid(b), "-".join(sorted([a, b]))
        cls = " ".join(["edge", "path" if k in pe else "", "mst" if k in me else ""])
        h.append(f'<line class="{cls}" x1="{A["x"]}" y1="{A["y"]}" x2="{B["x"]}" y2="{B["y"]}"/>')
    for a, b, w in EDGES:
        A, B = sid(a), sid(b)
        h.append(f'<text class="wlab" x="{(A["x"] + B["x"]) / 2}" y="{(A["y"] + B["y"]) / 2}">{w}</text>')
    for s in STOPS:
        cls = "node"
        if s["id"] in on_path: cls += " on"
        if src == s["id"]: cls += " src"
        if dst == s["id"]: cls += " dst"
        if pick: cls += " pick"
        r, extra = 21, ""
        if demand:
            d = S["demand"][s["id"]]["n"]
            r = 17 + jsround(d / max_d * 10)
            extra = f' style="fill:color-mix(in srgb, var(--brand) {jsround(d / max_d * 55)}%, var(--surface))"'
        lp = s["lp"]
        lx = s["x"] + r + 8 if lp == "r" else s["x"] - r - 8 if lp == "l" else s["x"]
        ly = s["y"] - r - 10 if lp == "t" else s["y"] + r + 14 if lp == "b" else s["y"] + 1
        anchor = "start" if lp == "r" else "end" if lp == "l" else "middle"
        g = (f'<g class="{cls}" data-id="{s["id"]}" aria-label="{esc(s["name"])}">'
             f'<circle cx="{s["x"]}" cy="{s["y"]}" r="{r}"{extra}/>'
             f'<text class="code" x="{s["x"]}" y="{s["y"]}">{s["id"]}</text>'
             f'<text class="nm" x="{lx}" y="{ly}" text-anchor="{anchor}" dominant-baseline="central">{esc(s["short"])}</text></g>')
        h.append(f'<a href="{esc(pick(s["id"]))}">{g}</a>' if pick else g)
    if bus:
        h.append(f'<g class="bus" id="bus" transform="translate({bus[0]} {bus[1]})"><circle class="ring" r="22"/>'
                 '<rect x="-14" y="-9" width="28" height="18" rx="4"/><rect class="win" x="-10" y="-6" width="8" height="5" rx="1"/>'
                 '<rect class="win" x="2" y="-6" width="8" height="5" rx="1"/><circle class="wh" cx="-8" cy="9" r="3"/>'
                 '<circle class="wh" cx="8" cy="9" r="3"/></g>')
    return "".join(h) + "</svg>"


def legend(m):
    return ('<div class="legend"><span><i></i>Shortest route</span>'
            + ('<span><i class="m"></i>Minimum network</span>' if m else "")
            + '<span><i class="g"></i>Road (minutes)</span></div>')


def stop_opts(sel):
    return "".join(f'<option value="{s["id"]}"{" selected" if s["id"] == sel else ""}>{esc(s["name"])}</option>' for s in STOPS)


# ------------------------------------------------------------------ verification (live checks)
def verification():
    out = []
    add = lambda name, ok, detail: out.append({"name": name, "pass": ok, "detail": detail})
    mism = bad = 0
    for s in range(G["n"]):
        r = dijkstra(G, s)
        for t in range(G["n"]):
            if r["dist"][t] != FW[s][t]: mism += 1
            if edge_sum(G, path_to(r["prev"], s, t)) != r["dist"][t]: bad += 1
    add("Dijkstra agrees with Floyd-Warshall", mism == 0, f"{G['n'] ** 2} stop pairs compared, {mism} differences")
    add("Route time equals the sum of its road weights", bad == 0, f"{G['n'] ** 2} reconstructed paths checked")
    k, prim = MST(), prim_weight(G)
    add("Kruskal network is a spanning tree", len(k["mst"]) == G["n"] - 1 and k["total"] == prim,
        f"{len(k['mst'])} edges for {G['n']} stops, weight {k['total']}, Prim gives {prim}")
    tw = trips_with_end(); sel = activity_selection(tw)
    overlap = any(sel[i]["start"] < sel[i - 1]["end"] for i in range(1, len(sel)))
    best = max_compatible_dp(tw)
    add("Selected trips do not overlap and are maximal", not overlap and len(sel) == best,
        f"{len(sel)} selected, DP maximum is {best}")
    cap, items = fleet_by(S["alloc"])["cap"], demand_items()
    f, z = fractional_knapsack(items, cap), knapsack01(items, cap)
    add("Seat allocations stay within capacity", f["used"] <= cap and z["used"] <= cap,
        f"Fractional uses {f['used']}, 0/1 uses {z['used']} of {cap} seats")
    add("0/1 value never beats the fractional bound", z["value"] <= f["value"] + 1e-9,
        f"0/1 {z['value']} is at most fractional {f['value']:.1f}")
    return out


def checks_html():
    return '<ul class="checks">' + "".join(
        f'<li><span class="pill {"good" if c["pass"] else "crit"}">{"Pass" if c["pass"] else "Fail"}</span>'
        f'<span><b>{c["name"]}</b><small>{c["detail"]}</small></span></li>' for c in verification()) + "</ul>"


# ------------------------------------------------------------------ page shell
NAV = {
    "passenger": [("plan", "Plan journey", "route"), ("timetable", "Timetable", "cal")],
    "admin": [("overview", "Overview", "grid"), ("network", "Network", "net"), ("fleet", "Fleet and demand", "bus"),
              ("lab", "Algorithm lab", "flask"), ("sched", "Scheduling", "clock")],
}
TITLES = {
    "plan": ("Plan your journey", "Pick two stops, enter your group size and watch the shuttle take the shortest road."),
    "timetable": ("Timetable", "Shuttle runs chosen so that no two overlap on the same vehicle."),
    "overview": ("Operations overview", "Demand, fleet and schedule status for the Woxsen campus shuttle."),
    "network": ("Campus network", "The shortest route and the cheapest connected road network, drawn on the same graph."),
    "fleet": ("Fleet and demand", "Edit waiting passengers and shuttle capacity. Seat allocation recalculates when you save."),
    "lab": ("Algorithm lab", "Run each algorithm on the live campus data and inspect every step."),
    "sched": ("Scheduling", "Add or remove trips. Activity Selection keeps the largest set that does not overlap."),
}
DOC = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
       '<meta name="viewport" content="width=device-width,initial-scale=1"><title>RouteLab | Woxsen campus shuttle</title>'
       '<link rel="stylesheet" href="/static/style.css"></head><body><div id="root">{}</div>{}</body></html>')


def html(body, script=""):
    return Response(DOC.format(body, script), mimetype="text/html")


def current(pid, page_id):
    return ' aria-current="page"' if pid == page_id else ""


def shell(page_id, inner, script=""):
    role = session["role"]
    nav = "".join(
        f'<form action="/{pid}" method="get"><button{current(pid, page_id)}>{icon(ic)}<span>{label}</span></button></form>'
        for pid, label, ic in NAV[role])
    t, d = TITLES[page_id]
    return html(f"""<div class="shell"><aside class="side">
      <div class="brand"><div class="brand-mark">{icon('bus')}</div><div><b>RouteLab</b><small>Woxsen shuttle</small></div></div>
      <nav class="nav" aria-label="Main">{nav}</nav>
      <div class="side-foot"><div class="who">{esc(session['email'])}</div>
        <form action="/logout" method="post"><button class="btn sm" aria-label="Sign out">{icon('out')}<span class="lo">Sign out</span></button></form></div>
    </aside><main class="main"><div id="page"><div class="page-head"><div><h1>{t}</h1><p>{d}</p></div>
      <span class="pill role-chip">{'Administrator' if role == 'admin' else 'Passenger'}</span></div><div id="body">{inner}</div></div></main></div>""", script)


def need(role):
    """Guard: returns a redirect if the visitor is not signed in with the right role."""
    if "role" not in session:
        return redirect("/login")
    if session["role"] != role:
        return redirect("/" + NAV[session["role"]][0][0])
    return None


# ------------------------------------------------------------------ login / logout
@app.route("/")
def home():
    return redirect("/" + NAV[session["role"]][0][0] if "role" in session else "/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    role = request.values.get("role", "passenger")
    role = role if role in USERS else "passenger"
    err = ""
    if request.method == "POST" and "pick" not in request.form:
        u = USERS[role]
        if request.form.get("email", "").strip().lower() == u["email"] and request.form.get("password") == u["password"]:
            session["role"], session["email"] = role, u["email"]
            return redirect("/" + NAV[role][0][0])
        err = (f'<div class="msg err">Email or password does not match the demo {role} account. '
               'Use the credentials shown below the button.</div>')
    u = USERS[role]
    m = map_svg(path=["MG", "AI", "AB", "LB", "T5"], src="MG", dst="T5", label="Decorative map of campus stops")
    seg = "".join(
        f'<button type="submit" formmethod="get" formaction="/login" formnovalidate name="role" value="{r}" '
        f'aria-pressed="{"true" if r == role else "false"}">{lbl}</button>'
        for r, lbl in (("passenger", "Passenger"), ("admin", "Administrator")))
    return html(f"""<div class="login">
    <section class="login-art"><div class="login-art-in">
      <div class="eyebrow">DAA project &middot; Group 13</div>
      <h1>Shuttle routes for the Woxsen campus.</h1>
      <p>RouteLab plans the quickest road between stops, fills seats fairly and schedules trips that do not collide. Every result comes from six algorithms running on one shared graph.</p>
      <div class="login-stats"><div><b>{len(STOPS)}</b><span>Campus stops</span></div><div><b>{len(EDGES)}</b><span>Shuttle roads</span></div><div><b>6</b><span>DAA algorithms</span></div></div>
      <div class="login-map">{m}</div></div></section>
    <section class="login-form-wrap"><form class="login-card" method="post" action="/login" autocomplete="off">
      <input type="hidden" name="role" value="{role}">
      <div><div class="eyebrow" style="color:var(--brand)">Local demo</div><h2>Welcome back</h2></div>
      <div class="seg" role="group" aria-label="Role">{seg}</div>
      <label class="field"><span>Email</span><input name="email" type="email" required value="{u['email']}"></label>
      <label class="field"><span>Password</span><input name="password" type="password" required value="{u['password']}"></label>
      <div role="alert">{err}</div>
      <button class="btn primary" type="submit">Open {'administrator' if role == 'admin' else 'passenger'} dashboard</button>
      <div class="cred"><span class="muted">Demo credentials</span><code>{u['email']} / {u['password']}</code></div>
      <p class="muted" style="margin:0;font-size:12px">Fixed credentials for classroom use. This is not production authentication.</p>
    </form></section></div>""")


@app.post("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================================================================== PASSENGER: PLAN
SIM_JS = """<script>
/* Shuttle animation only. All route and seat numbers are computed in Python. */
(function(){
  var D = window.SIM; if (!D || !D.segs.length) return;
  var $ = function(s){return document.querySelector(s);};
  var t = 0, running = false, speed = 2, last = 0, raf = 0, logged = 0;
  function pos(t){ var g = D.segs.find(function(g){return t <= g.t1;}) || D.segs[D.segs.length-1];
    var f = Math.min(1, Math.max(0, (t-g.t0)/g.w)); return [g.ax+(g.bx-g.ax)*f, g.ay+(g.by-g.ay)*f]; }
  function btn(label, svg){ $('#sstart').innerHTML = svg + '<span>' + label + '</span>'; }
  var PLAY = D.play, PAUSE = '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M8 5v14M16 5v14"/></svg>';
  function paint(){
    var q = pos(t); $('#bus').setAttribute('transform','translate('+q[0]+' '+q[1]+')');
    $('#sprog').style.width = (t/D.total*100)+'%';
    var done = t >= D.total;
    $('#sstat').textContent = done ? 'Arrived' : running ? 'En route' : t > 0 ? 'Paused' : 'Ready';
    $('#seta').textContent = done ? '0 min' : (D.total-t).toFixed(1)+' min';
    $('#socc').textContent = D.board+' / '+D.cap;
    while (logged < D.segs.length && t >= D.segs[logged].t1 - 1e-9){
      var g = D.segs[logged++], li = document.createElement('li');
      li.innerHTML = '<span class="t">t+'+g.t1.toFixed(1)+'</span><span>'+(logged===D.segs.length?'Arrived at ':'Passing ')+g.name+'</span>';
      $('#slog').appendChild(li); $('#slog').scrollTop = 1e6; }
  }
  function reset(){ cancelAnimationFrame(raf); running=false; t=0; logged=0;
    $('#slog').innerHTML = '<li><span class="t">t+0.0</span><span>Departs '+D.src+' with '+D.board+' passengers</span></li>';
    btn('Start shuttle', PLAY); paint(); }
  function tick(ts){ if(!running) return; t = Math.min(D.total, t + (ts-last)/1000*speed); last = ts; paint();
    if (t >= D.total){ running=false; btn('Run again', PLAY); return; } raf = requestAnimationFrame(tick); }
  $('#sstart').onclick = function(){
    if (running){ running=false; cancelAnimationFrame(raf); btn('Resume', PLAY); paint(); return; }
    if (t >= D.total) reset();
    running = true; last = performance.now(); btn('Pause', PAUSE); raf = requestAnimationFrame(tick); };
  $('#sreset').onclick = reset;
  document.querySelectorAll('#sspd button').forEach(function(b){ b.onclick = function(){ speed = +b.dataset.v;
    document.querySelectorAll('#sspd button').forEach(function(x){x.setAttribute('aria-pressed', String(x===b));}); }; });
  reset();
})();
</script>"""


def parse_pos_int(v, default):
    if v is None or v == "":
        return default
    try:
        n = float(v)
        return int(n) if n == int(n) else None
    except ValueError:
        return None


def leg_tag(legs, k):
    return f'<span class="leg">{legs[k]}m</span>' if k < len(legs) else ""


@app.route("/plan")
def plan():
    if (g := need("passenger")): return g
    a = request.args
    src, dst = a.get("src", "MG"), a.get("dst", "T5")
    src = src if src in G["idx"] else "MG"
    dst = dst if dst in G["idx"] else "T5"
    shuttle = a.get("shuttle", "SH-01")
    if shuttle not in [f["id"] for f in S["fleet"]]: shuttle = S["fleet"][0]["id"]
    pax = parse_pos_int(a.get("pax"), 35)
    cap = parse_pos_int(a.get("cap"), fleet_by(shuttle)["cap"])
    pick = a.get("pick", "src")

    err = ""
    if src == dst: err = "Choose two different stops. The destination is the same as the starting point."
    elif pax is None or pax < 1: err = "Passengers must be a whole number of at least 1."
    elif cap is None or cap < 1: err = "Shuttle capacity must be a whole number of at least 1."
    ok = not err
    r = route(src, dst) if src != dst else None

    def pick_url(stop):
        if pick == "src": return "/plan?" + qs(src=stop, dst=dst, pax=pax, shuttle=shuttle, cap=cap, pick="dst")
        return "/plan?" + qs(src=src, dst=stop, pax=pax, shuttle=shuttle, cap=cap, pick="src")

    # ---- result card
    if not r:
        result = '<div class="empty">Choose two different stops to see the shortest route.</div>'
    else:
        legs = [road(r["path"][i], r["path"][i + 1]) for i in range(len(r["path"]) - 1)]
        chain = "".join(f'<li>{esc(short(i))}{leg_tag(legs, k)}</li>'
                        for k, i in enumerate(r["path"]))
        extra = ""
        if ok:
            board, left = min(pax, cap), max(cap - pax, 0)
            wait, trips = max(pax - cap, 0), math.ceil(pax / max(cap, 1))
            pct = min(100, jsround(pax / max(cap, 1) * 100))
            cands = sorted((c for c in ({"f": f, "d": dist(f["loc"], src), "free": f["cap"] - f["occ"]} for f in S["fleet"])
                            if c["free"] >= pax), key=lambda c: c["d"])
            sug = (f'<b>Nearest shuttle:</b> {cands[0]["f"]["id"]} at {esc(short(cands[0]["f"]["loc"]))}, {cands[0]["d"]} min from pickup with {cands[0]["free"]} free seats.'
                   if cands else f'<b>Nearest shuttle:</b> no single shuttle has {pax} free seats right now. Split the group across two runs.')
            msg = (f'<div class="msg warn" style="margin-top:12px">{board} passengers board now. {wait} must wait for another run. {trips} trips are needed for this group.</div>'
                   if wait else f'<div class="msg ok" style="margin-top:12px">All {pax} passengers fit on one shuttle.</div>')
            extra = (f'<div class="facts"><div class="fact"><b>{pax}</b><span>Passengers</span></div><div class="fact"><b>{cap}</b><span>Capacity</span></div>'
                     f'<div class="fact"><b>{left}</b><span>Seats remaining</span></div></div>'
                     f'<div class="seatbar {"over" if pax > cap else ""}" role="img" aria-label="{pct}% of seats requested"><i style="width:{min(100, pct)}%"></i></div>'
                     f'{msg}<p style="margin:12px 0 0;font-size:13px">{sug}</p>')
        n_roads = len(r["path"]) - 1
        result = (f'<div class="card-h"><span>Fastest route</span><span class="pill route">Dijkstra</span></div>'
                  f'<div class="big-time"><b>{r["time"]}</b><span class="muted">minutes, {n_roads} road{"" if len(r["path"]) == 2 else "s"}</span></div>'
                  f'<ol class="chain">{chain}</ol><p class="muted mono" style="font-size:12px;margin:10px 0 0">{" + ".join(map(str, legs))} = {r["time"]} min</p>{extra}')

    fleet_opts = "".join(f'<option value="{f["id"]}"{" selected" if f["id"] == shuttle else ""}>{f["id"]}</option>' for f in S["fleet"])
    auto = 'onchange="this.form.submit()"'
    body = f"""<div class="grid plan-grid"><div class="stack">
      <section class="card"><h2>Where are you going?</h2>
      <form class="stack" method="get" action="/plan"><input type="hidden" name="pick" value="{pick}">
        <div class="row"><label class="field"><span>From</span><select name="src" {auto}>{stop_opts(src)}</select></label>
          <a class="btn" href="/plan?{qs(src=dst, dst=src, pax=pax, shuttle=shuttle, cap=cap)}" aria-label="Swap from and to" style="padding:0 10px">{icon('swap')}</a>
          <label class="field"><span>To</span><select name="dst" {auto}>{stop_opts(dst)}</select></label></div>
        <div class="row wrap"><label class="field"><span>Passengers</span><input name="pax" type="number" min="1" max="200" value="{pax if pax is not None else a.get('pax', '')}" {auto}></label>
          <label class="field"><span>Shuttle</span><select name="shuttle" onchange="this.form.cap.value='';this.form.submit()">{fleet_opts}</select></label>
          <label class="field"><span>Capacity</span><input name="cap" type="number" min="1" max="200" value="{cap if cap is not None else a.get('cap', '')}" {auto}></label></div>
        <div role="alert">{f'<div class="msg err">{err}</div>' if err else ''}</div>
        <button class="btn primary" type="submit">Find shortest route</button></form></section>
      <section class="card" id="result">{result}</section></div>
    <section class="card"><div class="card-h"><span>Campus map</span><span class="muted" style="font-size:12px;font-weight:400">Click a stop to set From, then To</span></div>
      <div class="map-box">{map_svg(path=r['path'] if r else [], src=src, dst=dst, pick=pick_url, bus=(sid(r['path'][0])['x'], sid(r['path'][0])['y']) if r else None)}</div>{legend(False)}
      <div class="sim-bar"><div class="btns"><button type="button" class="btn primary sm" id="sstart">{icon('play')}<span>Start shuttle</span></button>
        <button type="button" class="btn sm" id="sreset">{icon('reset')}<span>Reset</span></button></div>
        <div class="seg" id="sspd" role="group" aria-label="Simulation speed">{''.join(f'<button type="button" data-v="{v}" aria-pressed="{"true" if v == 2 else "false"}">{v}&times;</button>' for v in (1, 2, 4))}</div></div>
      <div class="progress" style="margin-top:12px"><i id="sprog"></i></div>
      <div class="tiles"><div class="tile"><span class="lbl">Status</span><b id="sstat">Ready</b></div><div class="tile"><span class="lbl">Arrives in</span><b id="seta">-</b></div><div class="tile"><span class="lbl">Onboard</span><b id="socc">-</b></div></div>
      <ul class="log" id="slog" aria-live="polite"></ul>
      <p class="muted" style="font-size:12px;margin:10px 0 0">Simulated movement along the calculated route. No GPS data is used.</p></section></div>"""

    script = ""
    if r and ok:
        segs, t0 = [], 0
        for i in range(len(r["path"]) - 1):
            A, B = sid(r["path"][i]), sid(r["path"][i + 1])
            w = road(A["id"], B["id"])
            segs.append({"ax": A["x"], "ay": A["y"], "bx": B["x"], "by": B["y"], "w": w, "t0": t0, "t1": t0 + w, "name": B["short"]})
            t0 += w
        sim = {"segs": segs, "total": t0, "board": min(pax, cap), "cap": cap, "src": short(src), "play": icon("play")}
        script = f"<script>window.SIM={json.dumps(sim)};</script>" + SIM_JS
    return shell("plan", body, script)


# ================================================================== PASSENGER: TIMETABLE
@app.route("/timetable")
def timetable():
    if (g := need("passenger")): return g
    tw = trips_with_end(); sel = activity_selection(tw)
    first = (fmt_t(sel[0]["start"]), esc(short(sel[0]["from"]))) if sel else ("-", "")
    lastr = (fmt_t(sel[-1]["end"]), esc(short(sel[-1]["to"]))) if sel else ("-", "")
    rows = "".join(f'<tr><td class="num">{fmt_t(t["start"])}</td><td>{esc(nm(t["from"]))}</td><td>{esc(nm(t["to"]))}</td>'
                   f'<td class="n">{dist(t["from"], t["to"])} min</td><td class="n">{fmt_t(t["end"])}</td></tr>' for t in sel)
    rows = rows or '<tr><td colspan="5"><div class="empty">No runs scheduled.</div></td></tr>'
    return shell("timetable", f"""<div class="grid kpis"><div class="card kpi"><span class="lbl">Scheduled runs</span><b>{len(sel)}</b><small>out of {len(tw)} requested</small></div>
      <div class="card kpi"><span class="lbl">First departure</span><b class="num">{first[0]}</b><small>{first[1]}</small></div>
      <div class="card kpi"><span class="lbl">Last arrival</span><b class="num">{lastr[0]}</b><small>{lastr[1]}</small></div></div>
      <section class="card"><h2>Today's runs</h2><div class="tbl-wrap"><table><thead><tr><th>Departs</th><th>From</th><th>To</th><th class="n">Travel</th><th class="n">Back at</th></tr></thead><tbody>{rows}</tbody></table></div>
      <p class="muted" style="font-size:12px;margin:12px 0 0">Back-at time includes {TURNAROUND} minutes for boarding and turnaround.</p></section>""")


# ================================================================== ADMIN: OVERVIEW
def fleet_table():
    cls = lambda s: "good" if s == "Active" else "warn" if s == "Maintenance" else "route"
    rows = "".join(f'<tr><td class="mono">{f["id"]}</td><td>{esc(f["driver"])}</td><td><span class="pill {cls(f["status"])}">{f["status"]}</span></td>'
                   f'<td>{esc(short(f["loc"]))}<div class="muted" style="font-size:12px">{esc(f["route"])}</div></td><td class="n">{f["occ"]} / {f["cap"]}</td></tr>'
                   for f in S["fleet"])
    return f'<div class="tbl-wrap"><table><thead><tr><th>Shuttle</th><th>Driver</th><th>Status</th><th>Location</th><th class="n">Seats</th></tr></thead><tbody>{rows}</tbody></table></div>'


@app.route("/overview")
def overview():
    if (g := need("admin")): return g
    total = sum(S["demand"][s["id"]]["n"] for s in STOPS)
    sel = activity_selection(trips_with_end())
    active = sum(f["status"] == "Active" for f in S["fleet"])
    max_d = max([1] + [S["demand"][s["id"]]["n"] for s in STOPS])
    ordered = sorted(STOPS, key=lambda s: -S["demand"][s["id"]]["n"])
    top = {s["id"] for s in ordered[:3]}
    bars = "".join(f'<div class="bar-row {"top" if s["id"] in top else ""}"><span>{esc(s["short"])}</span><div class="tr"><i style="width:{S["demand"][s["id"]]["n"] / max_d * 100}%"></i></div><b class="num">{S["demand"][s["id"]]["n"]}</b></div>' for s in ordered)
    return shell("overview", f"""<div class="grid kpis">
      <div class="card kpi"><span class="lbl">Passengers waiting</span><b>{total}</b><small>across {len(STOPS)} stops</small></div>
      <div class="card kpi"><span class="lbl">Active shuttles</span><b>{active} / {len(S['fleet'])}</b><small>{len(S['fleet']) - active} ready to dispatch</small></div>
      <div class="card kpi"><span class="lbl">Average route time</span><b>{avg_route():.1f} min</b><small>over every stop pair</small></div>
      <div class="card kpi"><span class="lbl">Scheduled trips</span><b>{len(sel)}</b><small>no overlaps</small></div></div>
    <div class="grid two">
      <section class="card"><div class="card-h"><span>Demand by stop</span><span class="muted" style="font-size:12px;font-weight:400">Top three highlighted</span></div><div class="bars">{bars}</div></section>
      <section class="card"><div class="card-h"><span>Campus activity</span></div><div class="map-box">{map_svg(demand=True, label="Map with stops sized by passenger demand")}</div><p class="muted" style="font-size:12px;margin:10px 0 0">Larger, darker stops have more waiting passengers.</p></section>
      <section class="card"><div class="card-h"><span>Shuttle status</span></div>{fleet_table()}</section>
      <section class="card"><div class="card-h"><span>Verification</span><span class="pill good">Live checks</span></div>{checks_html()}</section></div>""")


# ================================================================== ADMIN: NETWORK
def net_args():
    a = request.args
    src = a.get("src", "MG") if a.get("src") in G["idx"] else "MG"
    dst = a.get("dst", "T5") if a.get("dst") in G["idx"] else "T5"
    return src, dst


@app.route("/network")
def network():
    if (g := need("admin")): return g
    src, dst = net_args()
    show_path, show_mst = request.args.get("path", "1") == "1", request.args.get("mst", "1") == "1"
    tog = request.args.get("toggle")
    if tog == "path": show_path = not show_path
    if tog == "mst": show_mst = not show_mst
    k = MST()
    r = route(src, dst) if src != dst else None
    dj = (f'<b>{r["time"]} min</b><span>{" &rarr; ".join(esc(short(i)) for i in r["path"])}</span>' if r
          else "<b>-</b><span>Choose two different stops</span>")
    return shell("network", f"""<section class="card"><form method="get" action="/network">
      <input type="hidden" name="path" value="{int(show_path)}"><input type="hidden" name="mst" value="{int(show_mst)}">
      <div class="row wrap" style="margin-bottom:14px"><label class="field" style="min-width:180px"><span>From</span><select name="src" onchange="this.form.submit()">{stop_opts(src)}</select></label>
      <label class="field" style="min-width:180px"><span>To</span><select name="dst" onchange="this.form.submit()">{stop_opts(dst)}</select></label>
      <div class="seg" role="group" aria-label="Layers"><button name="toggle" value="path" aria-pressed="{str(show_path).lower()}">Shortest route</button>
      <button name="toggle" value="mst" aria-pressed="{str(show_mst).lower()}">Minimum network</button></div></div></form>
      <div class="map-box">{map_svg(path=r['path'] if show_path and r else [], mst=k['mst'] if show_mst else [], src=src, dst=dst)}</div>{legend(True)}
      <div class="grid two" style="margin-top:14px"><div class="fact"><span>Dijkstra shortest path</span>{dj}</div>
      <div class="fact"><span>Kruskal minimum network</span><b>{k['total']} min total</b><span>{len(k['mst'])} roads connect all {len(STOPS)} stops. This is a backbone, not a passenger route.</span></div></div></section>""")


# ================================================================== ADMIN: FLEET AND DEMAND
def alloc_html():
    cap = fleet_by(S["alloc"])["cap"]
    items = demand_items()
    f, z = fractional_knapsack(items, cap), knapsack01(items, cap)
    pct = lambda u: jsround(u / cap * 100)
    picked = ", ".join(f'{esc(x["name"])} ({x["w"]})' for x in z["picked"]) or "none"
    return f"""<div class="two grid" style="gap:12px">
      <div class="fact"><span>0/1 Knapsack (whole groups)</span><b>{z['used']} / {cap} seats</b><span>Value {z['value']}, {z['left']} seats free</span><div class="seatbar"><i style="width:{pct(z['used'])}%"></i></div></div>
      <div class="fact"><span>Fractional Knapsack (split groups)</span><b>{f['used']} / {cap} seats</b><span>Value {f['value']:.1f}, upper bound</span><div class="seatbar"><i style="width:{pct(f['used'])}%"></i></div></div></div>
      <p style="margin:12px 0 6px;font-size:13px"><b>Groups boarded (whole):</b> {picked}</p>
      <p class="muted" style="margin:0;font-size:12px">Value is passengers multiplied by their average wait in minutes, so the longest-waiting groups get seats first.</p>"""


@app.route("/fleet", methods=["GET", "POST"])
def fleet():
    if (g := need("admin")): return g
    if request.method == "POST":
        f = request.form
        for s in STOPS:
            S["demand"][s["id"]]["n"] = clamp_int(f.get(f"n_{s['id']}"), 0, 200)
            S["demand"][s["id"]]["w"] = clamp_int(f.get(f"w_{s['id']}"), 0, 60)
        for sh in S["fleet"]:
            sh["cap"] = clamp_int(f.get(f"cap_{sh['id']}"), 1, 200) or 1
            if f.get(f"st_{sh['id']}") in ("Active", "Available", "Maintenance"): sh["status"] = f[f"st_{sh['id']}"]
        if f.get("ash") in [x["id"] for x in S["fleet"]]: S["alloc"] = f["ash"]
        return redirect("/fleet")
    d_rows = "".join(f'<tr><td>{esc(s["short"])}</td><td class="n"><input class="cell-in" type="number" min="0" max="200" name="n_{s["id"]}" value="{S["demand"][s["id"]]["n"]}" aria-label="Waiting at {esc(s["short"])}"></td>'
                     f'<td class="n"><input class="cell-in" type="number" min="0" max="60" name="w_{s["id"]}" value="{S["demand"][s["id"]]["w"]}" aria-label="Average wait at {esc(s["short"])}"></td></tr>' for s in STOPS)
    def status_opts(cur):
        return "".join(f'<option{" selected" if o == cur else ""}>{o}</option>' for o in ("Active", "Available", "Maintenance"))
    f_rows = "".join(f'<tr><td><span class="mono">{x["id"]}</span><div class="muted" style="font-size:12px">{esc(x["driver"])}</div></td>'
                     f'<td><select class="cell-in" style="width:130px" name="st_{x["id"]}">{status_opts(x["status"])}</select></td>'
                     f'<td class="n"><input class="cell-in" type="number" min="1" max="200" name="cap_{x["id"]}" value="{x["cap"]}" aria-label="Capacity of {x["id"]}"></td></tr>' for x in S["fleet"])
    ash = "".join(f'<option value="{x["id"]}"{" selected" if x["id"] == S["alloc"] else ""}>{x["id"]}</option>' for x in S["fleet"])
    return shell("fleet", f"""<form method="post" action="/fleet"><div class="grid two">
      <section class="card"><h2>Waiting passengers</h2><div class="tbl-wrap"><table><thead><tr><th>Stop</th><th class="n">Waiting</th><th class="n">Avg wait (min)</th></tr></thead><tbody>{d_rows}</tbody></table></div></section>
      <div class="stack"><section class="card"><h2>Shuttles</h2><div class="tbl-wrap"><table><thead><tr><th>Shuttle</th><th>Status</th><th class="n">Capacity</th></tr></thead><tbody>{f_rows}</tbody></table></div></section>
      <section class="card"><div class="card-h"><span>Seat allocation</span><label class="field" style="flex-direction:row;align-items:center;gap:8px"><span>Shuttle</span>
        <select name="ash" style="width:auto;min-height:34px;padding:0 8px;border:1px solid var(--line);border-radius:8px;background:var(--surface)">{ash}</select></label></div>{alloc_html()}
        <div style="margin-top:14px"><button class="btn primary" type="submit">Save and recalculate</button></div></section></div></div></form>""")


# ================================================================== ADMIN: ALGORITHM LAB
ALGOS = [("dijkstra", "Dijkstra", "Shortest path", "Graph", "O(V²)"),
         ("floyd", "Floyd–Warshall", "All-pairs matrix", "Dynamic programming", "O(V³)"),
         ("kruskal", "Kruskal", "Minimum network", "Graph and greedy", "O(E log E)"),
         ("activity", "Activity Selection", "Compatible trips", "Greedy", "O(n log n)"),
         ("frac", "Fractional Knapsack", "Partial seat split", "Greedy", "O(n log n)"),
         ("knap", "0/1 Knapsack", "Whole groups", "Dynamic programming", "O(nW)"),
         ("compare", "Compare all", "Timing and checks", "Benchmark", "")]


def gantt_html(trips, sel_ids):
    if not trips: return '<div class="empty">No trips yet. Add one below.</div>'
    rows = sorted(trips, key=lambda r: r["start"])
    t0 = math.floor(min(r["start"] for r in rows) / 15) * 15
    t1 = math.ceil(max(r["end"] for r in rows) / 15) * 15
    span = t1 - t0
    axis = "".join(f'<span style="left:{(t - t0) / span * 100}%">{fmt_t(t)}</span>' for t in range(t0, t1 + 1, 15))
    body = "".join(
        f'<div class="grow"><div class="glabel" title="{esc(nm(r["from"]))} to {esc(nm(r["to"]))}"><b>{fmt_t(r["start"])}</b>{esc(short(r["from"]))} &rarr; {esc(short(r["to"]))}</div>'
        f'<div class="gtrack"><div class="gbar {"sel" if r["id"] in sel_ids else "skip"}" style="left:{(r["start"] - t0) / span * 100}%;width:{(r["end"] - r["start"]) / span * 100}%">{"Selected" if r["id"] in sel_ids else "Skipped"}</div></div></div>'
        for r in rows)
    return f'<div class="gantt"><div class="gaxis">{axis}</div>{body}</div>'


def run_bench():
    cap, items, tw = fleet_by(S["alloc"])["cap"], demand_items(), trips_with_end()

    def bench(fn, n=200):
        t = time.perf_counter()
        for _ in range(n): fn()
        return (time.perf_counter() - t) / n * 1e6
    S["bench"] = {"dijkstra": bench(lambda: dijkstra(G, 0)), "floyd": bench(lambda: floyd(G, EDGES), 50),
                  "kruskal": bench(lambda: kruskal(G, EDGES)), "activity": bench(lambda: activity_selection(tw)),
                  "frac": bench(lambda: fractional_knapsack(items, cap)), "knap": bench(lambda: knapsack01(items, cap))}


def share_cls(frac):
    return "good" if frac == 1 else "warn" if frac > 0 else ""


def share_txt(frac):
    if frac == 1: return "Whole"
    if frac > 0: return "%d%% split" % jsround(frac * 100)
    return "Not boarded"


@app.route("/lab")
def lab():
    if (g := need("admin")): return g
    a = request.args.get("a", "dijkstra")
    if a not in [x[0] for x in ALGOS]: a = "dijkstra"
    src, dst = net_args()
    name = next(x for x in ALGOS if x[0] == a)
    cap = fleet_by(S["alloc"])["cap"]
    items = demand_items()
    if a == "dijkstra":
        r, run = route(src, dst), dijkstra(G, G["idx"][src])
        status = ('<div class="msg err">Choose two different stops.</div>' if src == dst else
                  f'<div class="msg ok" style="margin-bottom:12px"><b>{r["time"]} min:</b> {" &rarr; ".join(esc(short(i)) for i in r["path"])}</div>')
        rows = "".join(f'<tr class="{"hl" if STOPS[o["u"]]["id"] == dst else ""}"><td class="n">{i + 1}</td><td>{esc(STOPS[o["u"]]["name"])}</td><td class="n">{o["d"]}</td>'
                       f'<td>{"source" if o["via"] < 0 else esc(STOPS[o["via"]]["short"])}</td></tr>' for i, o in enumerate(run["order"]))
        out = (f'<p class="explain">Starts at the source with distance 0, then repeatedly finalises the unvisited stop with the smallest tentative distance and relaxes its roads. Predecessors rebuild the path.</p>'
               f'<form method="get" action="/lab"><input type="hidden" name="a" value="dijkstra"><div class="row wrap" style="margin-bottom:12px">'
               f'<label class="field" style="min-width:170px"><span>From</span><select name="src" onchange="this.form.submit()">{stop_opts(src)}</select></label>'
               f'<label class="field" style="min-width:170px"><span>To</span><select name="dst" onchange="this.form.submit()">{stop_opts(dst)}</select></label></div></form>{status}'
               f'<div class="tbl-wrap"><table><thead><tr><th class="n">Step</th><th>Stop finalised</th><th class="n">Distance</th><th>Reached via</th></tr></thead><tbody>{rows}</tbody></table></div>')
    elif a == "floyd":
        mx = max(max(row) for row in FW)
        hi, hj = request.args.get("i"), request.args.get("j")
        hi = int(hi) if hi and hi.isdigit() and int(hi) < G["n"] else None
        hj = int(hj) if hj and hj.isdigit() and int(hj) < G["n"] else None
        sel = hi is not None and hj is not None
        head = "".join(f'<th title="{esc(s["name"])}"{" class=hot" if sel and j == hj else ""}>{s["id"]}</th>' for j, s in enumerate(STOPS))
        body = "".join(f'<tr><th title="{esc(s["name"])}"{" class=hot" if sel and i == hi else ""}>{s["id"]}</th>' + "".join(
            f'<td class="{"diag" if i == j else ""}{" hot" if sel and i == hi and j == hj else ""}" style="--v:{FW[i][j] / mx}"><a href="/lab?a=floyd&i={i}&j={j}">{FW[i][j]}</a></td>'
            for j in range(G["n"])) + "</tr>" for i, s in enumerate(STOPS))
        info = (f'<b>{esc(STOPS[hi]["name"])}</b> to <b>{esc(STOPS[hj]["name"])}</b>: {FW[hi][hj]} min' if sel else "Select a cell to read the pair.")
        out = (f'<p class="explain">Every stop is tried in turn as an intermediate stop: D[i][j] = min(D[i][j], D[i][k] + D[k][j]). Each cell is the shortest travel time in minutes. Select a cell to highlight its row and column.</p>'
               f'<div class="tbl-wrap"><table class="matrix"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div>'
               f'<p class="muted" style="margin:12px 0 0;font-size:13px">{info}</p>')
    elif a == "kruskal":
        k = MST()
        label = {"accepted": "Accepted", "rejected": "Rejected, cycle", "unused": "Not needed"}
        rows = "".join(f'<tr class="{"hl" if e["status"] == "accepted" else "dim"}"><td>{esc(short(e["a"]))} &ndash; {esc(short(e["b"]))}</td><td class="n">{e["w"]}</td>'
                       f'<td><span class="pill {"good" if e["status"] == "accepted" else ""}">{label[e["status"]]}</span></td></tr>' for e in k["steps"])
        out = (f'<p class="explain">Roads are sorted by minutes. A road is accepted only when its two stops are in different components, which guarantees there is no cycle. Total weight <b>{k["total"]}</b> over <b>{len(k["mst"])}</b> roads.</p>'
               f'<div class="grid two"><div class="map-box">{map_svg(mst=k["mst"])}</div><div class="tbl-wrap" style="max-height:480px;overflow:auto"><table><thead><tr><th>Road</th><th class="n">Min</th><th>Decision</th></tr></thead><tbody>{rows}</tbody></table></div></div>')
    elif a == "activity":
        tw = trips_with_end(); sel = activity_selection(tw)
        spans = ", ".join(f'{fmt_t(t["start"])}&ndash;{fmt_t(t["end"])}' for t in sel) or "none"
        out = (f'<p class="explain">Trips are sorted by finish time. The earliest finisher is kept, then every later trip that starts at or after the last kept finish. This keeps the largest possible number of compatible trips on one shuttle.</p>'
               f'{gantt_html(tw, {t["id"] for t in sel})}<p style="margin:14px 0 0"><b>{len(sel)}</b> of {len(tw)} trips selected: {spans}</p>')
    elif a == "frac":
        f = fractional_knapsack(items, cap)
        rows = "".join(f'<tr class="{"" if x["take"] > 0 else "dim"}"><td>{esc(x["name"])}</td><td class="n">{x["w"]}</td><td class="n">{x["ratio"]:.1f}</td><td class="n">{x["take"]}</td>'
                       f'<td><span class="pill {share_cls(x["frac"])}">{share_txt(x["frac"])}</span></td></tr>' for x in f["rows"])
        out = (f'<p class="explain">Groups are ranked by value per seat (average wait). Seats are filled from the top and the last group may be split. Capacity: <b>{cap}</b> seats on {S["alloc"]}. Change demand or capacity on the Fleet and demand page.</p>'
               f'<div class="tbl-wrap"><table><thead><tr><th>Group</th><th class="n">Seats</th><th class="n">Value / seat</th><th class="n">Taken</th><th>Share</th></tr></thead><tbody>{rows}</tbody></table></div>'
               f'<p style="margin:14px 0 0"><b>{f["used"]}</b> seats used, total value <b>{f["value"]:.1f}</b>.</p>')
    elif a == "knap":
        z, f = knapsack01(items, cap), fractional_knapsack(items, cap)
        pick = {x["id"] for x in z["picked"]}
        rows = "".join(f'<tr class="{"hl" if x["id"] in pick else "dim"}"><td>{esc(x["name"])}</td><td class="n">{x["w"]}</td><td class="n">{x["v"]}</td>'
                       f'<td><span class="pill {"good" if x["id"] in pick else ""}">{"Boarded" if x["id"] in pick else "Left"}</span></td></tr>' for x in items if x["w"] > 0)
        out = (f'<p class="explain">DP[i][c] holds the best value using the first i groups within c seats. A group is either taken whole or skipped, and backtracking over the table recovers the chosen groups. Capacity: <b>{cap}</b> seats on {S["alloc"]}.</p>'
               f'<div class="tbl-wrap"><table><thead><tr><th>Group</th><th class="n">Seats</th><th class="n">Value</th><th>Decision</th></tr></thead><tbody>{rows}</tbody></table></div>'
               f'<p style="margin:14px 0 0"><b>{z["used"]}</b> seats used, <b>{z["left"]}</b> free, value <b>{z["value"]}</b>. The fractional bound is {f["value"]:.1f}, so splitting groups could add {f["value"] - z["value"]:.1f}.</p>')
    else:  # compare
        if S["bench"] is None or request.args.get("rerun"): run_bench()
        b = S["bench"]
        rows = "".join(f'<tr><td><b>{x[1]}</b></td><td>{x[3]}</td><td>{x[2]}</td><td class="n">{x[4]}</td><td class="n">{b[x[0]]:.1f} &micro;s</td></tr>' for x in ALGOS if x[0] != "compare")
        out = (f'<p class="explain">Each algorithm runs hundreds of times on the current campus data. Times are averages in microseconds and vary by device. On a graph this small they mainly show how the cost grows from O(V²) to O(V³).</p>'
               f'<div class="tbl-wrap"><table><thead><tr><th>Algorithm</th><th>Category</th><th>Used for</th><th class="n">Complexity</th><th class="n">Average time</th></tr></thead><tbody>{rows}</tbody></table></div>'
               f'<div style="margin:14px 0 18px"><a class="btn sm" href="/lab?a=compare&rerun=1">Run benchmark again</a></div>'
               f'<div class="card-h" style="margin-top:6px"><span>Verification</span></div>{checks_html()}')
    lst = "".join(f'<button name="a" value="{i}" aria-pressed="{str(i == a).lower()}"><b>{n}</b><small>{s}</small></button>' for i, n, s, *_ in ALGOS)
    cplx = f'<span class="pill cplx">{name[4]}</span>' if name[4] else ""
    head = f'<div class="card-h"><span>{name[1]}</span>{cplx}</div>'
    return shell("lab", f'<div class="lab"><form class="algo-list" method="get" action="/lab"><input type="hidden" name="src" value="{src}"><input type="hidden" name="dst" value="{dst}">{lst}</form><section class="card">{head}{out}</section></div>')


# ================================================================== ADMIN: SCHEDULING
@app.route("/sched", methods=["GET", "POST"])
def sched():
    if (g := need("admin")): return g
    err = ""
    if request.method == "POST":
        f = request.form
        if "del" in f:
            S["trips"] = [t for t in S["trips"] if t["id"] != int(f["del"])]
        elif "reset" in f:
            S["trips"], S["next_trip"] = copy.deepcopy(DEFAULT_TRIPS), 11
        else:
            frm, to, st = f.get("from"), f.get("to"), f.get("start", "")
            if frm not in G["idx"] or to not in G["idx"] or frm == to: err = "A trip needs two different stops."
            elif not st: err = "Enter a departure time."
            else:
                S["trips"].append({"id": S["next_trip"], "start": parse_t(st), "from": frm, "to": to})
                S["next_trip"] += 1
        if not err: return redirect("/sched")
    tw = trips_with_end(); sel = activity_selection(tw); ids = {t["id"] for t in sel}
    rows = sorted(tw, key=lambda t: t["start"])
    tlist = ('<div class="empty">No trips requested.</div>' if not rows else
             '<form method="post" action="/sched"><div class="tbl-wrap" style="max-height:340px;overflow:auto"><table><thead><tr><th>Trip</th><th class="n">Window</th><th>Result</th><th></th></tr></thead><tbody>'
             + "".join(f'<tr><td>{esc(short(t["from"]))} &rarr; {esc(short(t["to"]))}</td><td class="n">{fmt_t(t["start"])}&ndash;{fmt_t(t["end"])}</td>'
                       f'<td><span class="pill {"good" if t["id"] in ids else ""}">{"Selected" if t["id"] in ids else "Skipped"}</span></td>'
                       f'<td><button class="btn sm ghost" name="del" value="{t["id"]}" aria-label="Remove trip {fmt_t(t["start"])} {esc(short(t["from"]))} to {esc(short(t["to"]))}">Remove</button></td></tr>' for t in rows)
             + "</tbody></table></div></form>")
    return shell("sched", f"""<section class="card"><div class="card-h"><span>Trip timeline</span><span class="pill route">{len(sel)} of {len(tw)} selected</span></div>{gantt_html(tw, ids)}</section>
      <div class="grid two" style="margin-top:16px"><section class="card"><h2>Add a trip</h2><form class="stack" method="post" action="/sched">
        <div class="row wrap"><label class="field" style="min-width:140px"><span>From</span><select name="from">{stop_opts('MG')}</select></label>
        <label class="field" style="min-width:140px"><span>To</span><select name="to">{stop_opts('T5')}</select></label>
        <label class="field" style="max-width:130px"><span>Departs</span><input name="start" type="time" value="08:20" required></label></div>
        <div role="alert">{f'<div class="msg err">{err}</div>' if err else ''}</div>
        <div><button class="btn primary" type="submit">Add trip</button> <button class="btn" name="reset" value="1" formnovalidate>Restore sample trips</button></div>
        <p class="muted" style="margin:0;font-size:12px">Arrival is departure plus the shortest travel time plus {TURNAROUND} minutes for boarding and turnaround.</p></form></section>
      <section class="card"><h2>Requested trips</h2>{tlist}</section></div>""")


if __name__ == "__main__":
    app.run(debug=True)
