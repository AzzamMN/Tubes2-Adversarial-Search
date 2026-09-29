"""Eksperimen headless untuk engine battle di main.py (tanpa PyScript/browser).
Jalankan:  python3 experiments.py   (main.py harus satu folder)"""
import math, time, random, itertools, statistics, collections, json, sys, pathlib

src = pathlib.Path(__file__).with_name("main.py").read_text()
engine = src.split("# ==== BATTLE ENGINE BEGIN ====")[1].split("# ==== BATTLE ENGINE END ====")[0]
exec(engine, globals())

def rand_state(rng):
    s = new_battle()
    for _ in range(rng.randint(0, 8)):
        if is_terminal(s): break
        s = apply_action(s, rng.choice(legal_actions(s)))
    return s if (not is_terminal(s)) else new_battle()

def npc_root(rng):                       # state acak dengan giliran NPC
    while True:
        s = rand_state(rng)
        if s.turn == "N" and not is_terminal(s): return s

# ---------- kebijakan lawan (Player) ----------
def pol_random(s, rng): return rng.choice(legal_actions(s))
def pol_attacker(s, rng): return "attack"
def pol_minimax(depth=4, ev="balanced"):
    def f(s, rng): return search(mirror(s), depth, "alphabeta", ev)["action"]
    return f

def play(npc_cfg, opp, npc_first, rng):
    s = new_battle()
    s = s._replace(turn="N" if npc_first else "P")
    acts, nodes, tms, moves, rounds = collections.Counter(), 0, 0.0, 0, 0
    while not is_terminal(s) and rounds < 200:
        if s.turn == "N":
            r = search(s, **npc_cfg)
            a = r["action"]; nodes += r["nodes"]; tms += r["time_ms"]; moves += 1; acts[a] += 1
        else:
            a = opp(s, rng)
        s = apply_action(s, a); rounds += 1
    return dict(win=s.php <= 0, rounds=rounds, acts=acts, nodes=nodes, ms=tms, moves=moves,
                hp=s.nhp if s.php <= 0 else -s.php)

def match(npc_cfg, opp, n=100, seed=1):
    rng = random.Random(seed); R = [play(npc_cfg, opp, i % 2 == 0, rng) for i in range(n)]
    tot = sum(sum(r["acts"].values()) for r in R) or 1
    ac = collections.Counter(); [ac.update(r["acts"]) for r in R]
    return dict(win=100 * sum(r["win"] for r in R) / n, rounds=statistics.mean(r["rounds"] for r in R),
                atk=100 * ac["attack"] / tot, dfn=100 * ac["defend"] / tot, pot=100 * ac["potion"] / tot,
                nodes=sum(r["nodes"] for r in R) / max(1, sum(r["moves"] for r in R)),
                ms=sum(r["ms"] for r in R) / max(1, sum(r["moves"] for r in R)),
                hp=statistics.mean(r["hp"] for r in R))

OPPS = {"random": pol_random, "attacker": pol_attacker, "minimax-d4": pol_minimax(4)}
out = {}

# ===== 1. minimax vs alpha-beta vs early stop vs expectimax (node count) =====
rng = random.Random(7); states = [npc_root(rng) for _ in range(100)]
e1 = {}
for d in range(1, 11):
    row = {}
    for name, algo, lim in (("minimax", "minimax", None), ("alphabeta", "alphabeta", None),
                            ("early100", "alphabeta", 100), ("expectimax", "expectimax", None)):
        if algo == "minimax" and d > 9: continue
        rs = [search(s, d, algo, "balanced", "default", lim) for s in states[:30 if d > 8 else 100]]
        row[name] = (statistics.mean(r["nodes"] for r in rs), statistics.mean(r["time_ms"] for r in rs))
    e1[d] = row
out["e1"] = e1
same = sum(1 for s in states for d in (3, 5)
           if (lambda a, b: a["action"] == b["action"] and a["value"] == b["value"])(
               search(s, d, "minimax"), search(s, d, "alphabeta")))
out["e1_same"] = (same, len(states) * 2)
agree = sum(1 for s in states if search(s, 6, "alphabeta")["action"] == search(s, 6, "alphabeta", limit if False else "balanced", "default", 100)["action"]) if False else None
ag = sum(1 for s in states if search(s, 6, "alphabeta")["action"] == search(s, 6, "alphabeta", "balanced", "default", 100)["action"])
out["e1_early_agree"] = (ag, len(states))

# ===== 2 & 5. fungsi evaluasi + perilaku =====
out["e2"] = {ev: {o: match(dict(depth=4, algo="alphabeta", eval_name=ev), OPPS[o], 100) for o in OPPS}
             for ev in EVALS}

# ===== 3. urutan aksi =====
e3 = {}
for name in ORDERS:
    for d in (6, 8):
        rs = [search(s, d, "alphabeta", "balanced", name) for s in states[:50]]
        e3[(name, d)] = (statistics.mean(r["nodes"] for r in rs), statistics.mean(r["cutoffs"] for r in rs),
                         statistics.mean(r["time_ms"] for r in rs))
out["e3"] = e3

# ===== 4. kedalaman =====
out["e4"] = {d: {o: match(dict(depth=d, algo="alphabeta", eval_name="balanced"), OPPS[o], 100)
                 for o in ("random", "minimax-d4")} for d in range(1, 7)}

# ===== 6. expectimax =====
out["e6"] = {a: {o: match(dict(depth=4, algo=a, eval_name="balanced"), OPPS[o], 100) for o in OPPS}
             for a in ("minimax", "expectimax")}

def fmt(o):
    if isinstance(o, dict): return {str(k): fmt(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [fmt(x) for x in o]
    if isinstance(o, float): return round(o, 2)
    return o
json.dump(fmt(out), open("hasil_eksperimen.json", "w"), indent=1)
print(json.dumps(fmt(out), indent=1))
