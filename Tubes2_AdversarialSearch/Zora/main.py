import heapq
import math
import time
import itertools
from pyscript import document
from pyodide.ffi import create_proxy

# =====================================================================
# DATA PETA & KONFIGURASI (Disatukan agar bebas masalah cache Pyodide)
# =====================================================================
MAP_DATA = [
    "....................",
    "..####..............",
    "..#..#....^^^^......",
    "..#..#....^^^^......",
    "..#..#..............",
    "....................",
    "~~~~~~~~~=~~~~~~~~~~",
    "....................",
    "..........####......",
    "..........#..#......",
    "..........####......",
    "....................",
    "..^^^^..............",
    "..^^^^..............",
    "....................",
    "~~~~~~~~~~~~~~=~~~~~",
    "....................",
    "....................",
    "....................",
]

TILE = 30  # ukuran tiap sel grid dalam pixel

TILE_COLORS = {
    ".": "#3f6b34",
    "^": "#8a6d3b",
    "#": "#2b2f33",
    "~": "#235d82",
    "=": "#a9744a",
}

ALGO_LABELS = {
    "ucs": "UCS (Uniform Cost Search)",
    "astar_manhattan": "A* — Manhattan Distance",
    "astar_euclidean": "A* — Euclidean Distance",
}


# =====================================================================
# 1. CLASS NODE
# =====================================================================
class Node:
    __slots__ = ("pos", "g", "h", "parent")

    def __init__(self, pos, g, h, parent=None):
        self.pos = pos      # (x, y)
        self.g = g          # cost akumulatif dari start ke node ini
        self.h = h          # estimasi heuristik ke goal
        self.parent = parent

    @property
    def f(self):
        return self.g + self.h


# =====================================================================
# 2. CLASS GRIDMAP
# =====================================================================
class GridMap:
    COST = {".": 1, "^": 3, "=": 1}
    BLOCKED = {"#", "~"}

    def __init__(self, rows):
        self.rows = rows
        self.height = len(rows)
        self.width = len(rows[0])

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, pos):
        x, y = pos
        return self.rows[y][x]

    def walkable(self, pos):
        return self.in_bounds(pos) and self.tile(pos) not in self.BLOCKED

    def cost(self, pos):
        return self.COST.get(self.tile(pos), 1)

    def neighbors(self, pos):
        x, y = pos
        result = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            npos = (x + dx, y + dy)
            if self.walkable(npos):
                result.append((npos, self.cost(npos)))
        return result


# =====================================================================
# 3. FUNGSI HEURISTIK
# =====================================================================
def h_zero(a, b):
    return 0


def h_manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def h_euclidean(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


HEURISTICS = {
    "ucs": h_zero,
    "astar_manhattan": h_manhattan,
    "astar_euclidean": h_euclidean,
}


# =====================================================================
# 4. CLASS PATHFINDING
# =====================================================================
class Pathfinding:

    @staticmethod
    def search(grid, start, goal, heuristic_fn):
        t0 = time.perf_counter()
        counter = itertools.count()

        start_node = Node(start, g=0, h=heuristic_fn(start, goal))
        open_heap = [(start_node.f, next(counter), start_node)]
        open_lookup = {start: start_node}
        closed_set = set()
        expanded = 0

        while open_heap:
            f, _, current = heapq.heappop(open_heap)

            if current.pos in closed_set:
                continue

            closed_set.add(current.pos)
            expanded += 1

            if current.pos == goal:
                path = Pathfinding._reconstruct(current)
                exec_ms = (time.perf_counter() - t0) * 1000
                open_positions = {
                    node.pos for _, _, node in open_heap if node.pos not in closed_set
                }
                return {
                    "path": path,
                    "closed": closed_set,
                    "open": open_positions,
                    "cost": current.g,
                    "expanded": expanded,
                    "time_ms": exec_ms,
                }

            for npos, move_cost in grid.neighbors(current.pos):
                if npos in closed_set:
                    continue
                tentative_g = current.g + move_cost
                existing = open_lookup.get(npos)
                if existing is None or tentative_g < existing.g:
                    h = heuristic_fn(npos, goal)
                    node = Node(npos, tentative_g, h, current)
                    open_lookup[npos] = node
                    heapq.heappush(open_heap, (node.f, next(counter), node))

        exec_ms = (time.perf_counter() - t0) * 1000
        return {
            "path": None,
            "closed": closed_set,
            "open": set(),
            "cost": 0,
            "expanded": expanded,
            "time_ms": exec_ms,
        }

    @staticmethod
    def _reconstruct(node):
        path = []
        while node is not None:
            path.append(node.pos)
            node = node.parent
        path.reverse()
        return path


# =====================================================================
# 5. BATTLE ENGINE (turn-based: Minimax / Alpha-Beta / Expectimax)
# ==== BATTLE ENGINE BEGIN ====
# =====================================================================
from collections import namedtuple

MAX_HP = 100
ATK_DMG = 20          # damage attack normal
HEAL = 30             # heal potion
START_POTIONS = 2
WIN_SCORE = 1000
INF = math.inf

# php/nhp = HP player/NPC, ppot/npot = sisa potion, psh/nsh = shield aktif,
# turn = "P" (giliran player) atau "N" (giliran NPC = pemain MAX)
State = namedtuple("State", "php nhp ppot npot psh nsh turn")
ACTIONS = ("attack", "defend", "potion")
ORDERS = {
    "default": ("attack", "defend", "potion"),
    "reverse": ("potion", "defend", "attack"),
    "defend_first": ("defend", "potion", "attack"),
    "heuristic": "heuristic",   # urut berdasarkan evaluasi statis anak (best-first)
}


def new_battle():
    return State(MAX_HP, MAX_HP, START_POTIONS, START_POTIONS, False, False, "P")


def mirror(s):
    """Tukar peran Player <-> NPC (dipakai agar Player bisa dimainkan oleh minimax)."""
    return State(s.nhp, s.php, s.npot, s.ppot, s.nsh, s.psh, "N" if s.turn == "P" else "P")


def legal_actions(s):
    hp, pot, sh = (s.php, s.ppot, s.psh) if s.turn == "P" else (s.nhp, s.npot, s.nsh)
    acts = ["attack"]
    if not sh:
        acts.append("defend")
    if pot > 0 and hp < MAX_HP:
        acts.append("potion")
    return acts


def apply_action(s, a):
    if s.turn == "P":
        if a == "attack":
            dmg = ATK_DMG // 2 if s.nsh else ATK_DMG
            return s._replace(nhp=max(0, s.nhp - dmg), nsh=False, turn="N")
        if a == "defend":
            return s._replace(psh=True, turn="N")
        return s._replace(php=min(MAX_HP, s.php + HEAL), ppot=s.ppot - 1, turn="N")
    if a == "attack":
        dmg = ATK_DMG // 2 if s.psh else ATK_DMG
        return s._replace(php=max(0, s.php - dmg), psh=False, turn="P")
    if a == "defend":
        return s._replace(nsh=True, turn="P")
    return s._replace(nhp=min(MAX_HP, s.nhp + HEAL), npot=s.npot - 1, turn="P")


def is_terminal(s):
    return s.php <= 0 or s.nhp <= 0


def utility(s, d):
    """Utility dari sudut pandang NPC. d = sisa kedalaman -> menang lebih cepat lebih baik."""
    return (WIN_SCORE + d) if s.php <= 0 else -(WIN_SCORE + d)


# ---- Fungsi evaluasi (sudut pandang NPC; makin besar makin baik bagi NPC) ----
def eval_zero(s):
    return 0


def eval_hp(s):
    return s.nhp - s.php


def eval_balanced(s):
    return (s.nhp - s.php) + 12 * (s.npot - s.ppot) + 8 * (int(s.nsh) - int(s.psh))


def eval_aggressive(s):
    return 0.5 * s.nhp - 2.0 * s.php


def eval_defensive(s):
    return 2.0 * s.nhp - 0.5 * s.php + 12 * s.npot + 8 * int(s.nsh)


EVALS = {
    "zero": eval_zero, "hp": eval_hp, "balanced": eval_balanced,
    "aggressive": eval_aggressive, "defensive": eval_defensive,
}


def _ordered(s, order, ef):
    acts = legal_actions(s)
    if order == "heuristic":
        return sorted(acts, key=lambda a: ef(apply_action(s, a)), reverse=(s.turn == "N"))
    seq = ORDERS[order] if isinstance(order, str) else order
    return [a for a in seq if a in acts]


def search(state, depth, algo="alphabeta", eval_name="balanced", order="default", node_limit=None):
    """Root = giliran NPC (MAX). algo: minimax | alphabeta | expectimax.
    node_limit -> early stop: setelah budget node habis, node dipotong dan dinilai dengan eval."""
    t0 = time.perf_counter()
    ef = EVALS[eval_name]
    st = {"nodes": 1, "cutoffs": 0, "stopped": False}

    def value(s, d, alpha, beta):
        st["nodes"] += 1
        if is_terminal(s):
            return utility(s, d)
        if d == 0:
            return ef(s)
        if node_limit and st["nodes"] >= node_limit:
            st["stopped"] = True
            return ef(s)
        acts = _ordered(s, order, ef)
        if s.turn == "N":                       # MAX
            best = -INF
            for a in acts:
                v = value(apply_action(s, a), d - 1, alpha, beta)
                best = max(best, v)
                if algo == "alphabeta":
                    alpha = max(alpha, best)
                    if alpha >= beta:
                        st["cutoffs"] += 1
                        break
            return best
        if algo == "expectimax":                # CHANCE: lawan diasumsikan acak uniform
            return sum(value(apply_action(s, a), d - 1, alpha, beta) for a in acts) / len(acts)
        best = INF                              # MIN
        for a in acts:
            v = value(apply_action(s, a), d - 1, alpha, beta)
            best = min(best, v)
            if algo == "alphabeta":
                beta = min(beta, best)
                if alpha >= beta:
                    st["cutoffs"] += 1
                    break
        return best

    scores, best_a, best_v, alpha = {}, None, -INF, -INF
    for a in _ordered(state, order, ef):
        a0 = alpha
        v = value(apply_action(state, a), depth - 1, alpha, INF)
        exact = not (algo == "alphabeta" and best_a is not None and v <= a0)
        scores[a] = (v, exact)          # exact False -> v hanyalah batas atas (<=)
        if v > best_v:
            best_v, best_a = v, a
        if algo == "alphabeta":
            alpha = max(alpha, best_v)
    return {"action": best_a, "value": best_v, "scores": scores, "nodes": st["nodes"],
            "cutoffs": st["cutoffs"], "stopped": st["stopped"],
            "time_ms": (time.perf_counter() - t0) * 1000}
# ==== BATTLE ENGINE END ====


# =====================================================================
# 6. CLASS GAME

BATTLE_DIST = 2   # jarak Manhattan NPC-Player untuk memicu mode battle
ALGO_NAMES = {"minimax": "Minimax", "alphabeta": "Alpha-Beta",
              "alphabeta_early": "Alpha-Beta + Early Stop", "expectimax": "Expectimax"}
ACT_ID = {"attack": "btnAttack", "defend": "btnDefend", "potion": "btnPotion"}


class Game:
    KEY_MAP = {
        "ArrowUp": (0, -1), "w": (0, -1), "W": (0, -1),
        "ArrowDown": (0, 1), "s": (0, 1), "S": (0, 1),
        "ArrowLeft": (-1, 0), "a": (-1, 0), "A": (-1, 0),
        "ArrowRight": (1, 0), "d": (1, 0), "D": (1, 0),
    }
    BATTLE_KEYS = {"1": "attack", "2": "defend", "3": "potion"}

    START_PLAYER = (17, 2)
    START_NPC = (2, 18)

    def __init__(self):
        self.grid = GridMap(MAP_DATA)
        self.player = self.START_PLAYER
        self.npc = self.START_NPC
        self.algo = "astar_manhattan"
        self.last_result = None
        self.game_over = False
        self.mode = "explore"      # "explore" | "battle"
        self.bs = None             # State battle
        self.debug = None          # hasil analisis NPC terakhir
        self.log = []

        el = document.getElementById
        self.el = el
        self.canvas = el("gameCanvas")
        self.ctx = self.canvas.getContext("2d")
        self.stat_expanded = el("statExpanded")
        self.stat_cost = el("statCost")
        self.stat_time = el("statTime")
        self.stat_status = el("statStatus")

        self._proxies = []
        self._bind_events()
        self.recompute_npc_path()
        self.render()

    def _on(self, target, evt, fn):
        p = create_proxy(fn)
        self._proxies.append(p)
        target.addEventListener(evt, p)

    def _bind_events(self):
        self._on(document, "keydown", self.on_keydown)
        self._on(self.el("algoSelect"), "change", self.on_algo_change)
        self._on(self.el("resetBtn"), "click", self.on_reset)
        for act, bid in ACT_ID.items():
            self._on(self.el(bid), "click", lambda e, a=act: self.do_player_action(a))
        self._on(self.el("dbgToggle"), "change", lambda e: self.render())

    # ---------------- eksplorasi ----------------
    def on_algo_change(self, event):
        self.algo = event.target.value
        self.recompute_npc_path()
        self.render()

    def on_reset(self, event=None):
        self.player, self.npc = self.START_PLAYER, self.START_NPC
        self.game_over, self.mode, self.bs, self.debug, self.log = False, "explore", None, None, []
        self.el("battleSection").classList.add("hidden")
        self.recompute_npc_path()
        self.render()

    def on_keydown(self, event):
        key = event.key
        if self.mode == "battle":
            if key in self.BATTLE_KEYS:
                event.preventDefault()
                self.do_player_action(self.BATTLE_KEYS[key])
            return
        if self.game_over or key not in self.KEY_MAP:
            return
        event.preventDefault()
        dx, dy = self.KEY_MAP[key]
        target = (self.player[0] + dx, self.player[1] + dy)
        if self.grid.walkable(target):
            self.player = target
        self.step_npc()
        if h_manhattan(self.npc, self.player) <= BATTLE_DIST:
            self.start_battle()
        else:
            self.recompute_npc_path()
        self.render()

    def recompute_npc_path(self):
        self.last_result = Pathfinding.search(self.grid, self.npc, self.player, HEURISTICS[self.algo])

    def step_npc(self):
        r = self.last_result
        if r and r["path"] and len(r["path"]) > 1:
            self.npc = r["path"][1]

    # ---------------- battle ----------------
    def start_battle(self):
        self.mode, self.bs, self.debug = "battle", new_battle(), None
        self.log = ["Battle dimulai! Giliran Anda: Attack / Defend / Potion (tombol 1-2-3)."]
        self.el("battleSection").classList.remove("hidden")

    def add_log(self, msg):
        self.log = (self.log + [msg])[-7:]

    def do_player_action(self, action):
        if self.mode != "battle" or self.game_over or self.bs.turn != "P":
            return
        if action not in legal_actions(self.bs):
            self.add_log("Aksi tidak legal (sudah shield / potion habis / HP penuh).")
            self.render()
            return
        old = self.bs
        self.bs = apply_action(old, action)
        self.add_log(f"Player: {action} -> {self._delta(old, self.bs)}")
        if is_terminal(self.bs):
            self.end_battle()
        else:
            self.npc_turn()
        self.render()

    def npc_turn(self):
        v = lambda i: self.el(i).value
        depth, ev, order = int(v("battleDepth")), v("battleEval"), v("battleOrder")
        limit, sel = int(v("battleLimit")), v("battleAlgo")
        cfgs = {"minimax": ("minimax", None), "alphabeta": ("alphabeta", None),
                "alphabeta_early": ("alphabeta", limit), "expectimax": ("expectimax", None)}
        results = {n: search(self.bs, depth, a, ev, order, lim) for n, (a, lim) in cfgs.items()}
        main = results[sel]
        self.debug = {"sel": sel, "results": results, "depth": depth, "eval": ev, "order": order}
        old = self.bs
        self.bs = apply_action(old, main["action"])
        self.add_log(f"NPC ({ALGO_NAMES[sel]}, d={depth}): {main['action']} -> {self._delta(old, self.bs)}")
        if is_terminal(self.bs):
            self.end_battle()

    @staticmethod
    def _delta(a, b):
        return f"HP P {a.php}->{b.php}, HP NPC {a.nhp}->{b.nhp}"

    def end_battle(self):
        self.game_over = True
        self.add_log("NPC MENANG!" if self.bs.php <= 0 else "PLAYER MENANG!")

    # ---------------- render ----------------
    def render(self):
        ctx = self.ctx
        ctx.clearRect(0, 0, self.canvas.width, self.canvas.height)
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                ctx.fillStyle = TILE_COLORS.get(self.grid.tile((x, y)), "#000000")
                ctx.fillRect(x * TILE, y * TILE, TILE, TILE)
                ctx.strokeStyle = "rgba(0,0,0,0.18)"
                ctx.strokeRect(x * TILE, y * TILE, TILE, TILE)

        r = self.last_result
        if r and self.mode == "explore":
            for color, cells in (("rgba(255,60,60,0.38)", r["closed"]),
                                 ("rgba(255,220,60,0.40)", r["open"]),
                                 ("rgba(60,255,120,0.6)", r["path"] or [])):
                ctx.fillStyle = color
                for (x, y) in cells:
                    ctx.fillRect(x * TILE, y * TILE, TILE, TILE)

        self._draw_entity(self.npc, "#ff5470")
        self._draw_entity(self.player, "#4fc3f7")
        if self.mode == "battle":
            self._draw_hp(self.npc, self.bs.nhp)
            self._draw_hp(self.player, self.bs.php)
            if self.el("dbgToggle").checked:
                self._draw_debug()
            self._update_battle_panel()
        self._update_stats()

    def _draw_entity(self, pos, color):
        ctx = self.ctx
        cx, cy = pos[0] * TILE + TILE / 2, pos[1] * TILE + TILE / 2
        ctx.beginPath()
        ctx.arc(cx, cy, TILE * 0.34, 0, 2 * math.pi)
        ctx.fillStyle = color
        ctx.fill()
        ctx.lineWidth = 2
        ctx.strokeStyle = "#0d1117"
        ctx.stroke()

    def _draw_hp(self, pos, hp):
        x, y = pos[0] * TILE, pos[1] * TILE - 5
        self.ctx.fillStyle = "#000"
        self.ctx.fillRect(x, y, TILE, 4)
        self.ctx.fillStyle = "#4cd964" if hp > 40 else "#ff9500" if hp > 20 else "#ff3b30"
        self.ctx.fillRect(x, y, TILE * hp / MAX_HP, 4)

    def _draw_debug(self):
        d = self.debug
        if not d:
            return
        ctx, main = self.ctx, d["results"][d["sel"]]
        lines = [f"NPC DEBUG  {ALGO_NAMES[d['sel']]}  depth={d['depth']}",
                 f"eval={d['eval']}  order={d['order']}", "-- skor aksi --"]
        for a, (val, exact) in main["scores"].items():
            lines.append(f"{'>' if a == main['action'] else ' '} {a:<7} {'' if exact else '<='}{val:.1f}")
        lines.append("-- node count --")
        for n, res in d["results"].items():
            lines.append(f"{ALGO_NAMES[n]:<24}{res['nodes']:>6}")
        h = 8 + 15 * len(lines)
        ctx.fillStyle = "rgba(0,0,0,0.78)"
        ctx.fillRect(6, 6, 330, h)
        ctx.font = "12px monospace"
        ctx.fillStyle = "#e6edf3"
        for i, ln in enumerate(lines):
            ctx.fillText(ln, 12, 22 + 15 * i)

    def _update_battle_panel(self):
        s, el = self.bs, self.el
        el("playerHpBar").style.width = f"{s.php}%"
        el("npcHpBar").style.width = f"{s.nhp}%"
        el("playerHpTxt").innerText = f"{s.php}/{MAX_HP} | potion {s.ppot} | shield {'ON' if s.psh else '-'}"
        el("npcHpTxt").innerText = f"{s.nhp}/{MAX_HP} | potion {s.npot} | shield {'ON' if s.nsh else '-'}"
        el("battleLog").innerHTML = "<br>".join(self.log)
        legal = legal_actions(s) if (not self.game_over and s.turn == "P") else []
        for act, bid in ACT_ID.items():
            el(bid).disabled = act not in legal
        d = self.debug
        if not d:
            el("debugTable").innerHTML = ""
            return
        main = d["results"][d["sel"]]
        rows = "".join(
            f"<tr><td>{'&#10003; ' if a == main['action'] else ''}{a}</td>"
            f"<td>{'' if ex else '&le; '}{v:.1f}</td></tr>" for a, (v, ex) in main["scores"].items())
        cmp_rows = "".join(
            f"<tr class=\"{'act' if n == d['sel'] else ''}\"><td>{ALGO_NAMES[n]}</td><td>{r['nodes']}</td>"
            f"<td>{r['cutoffs']}</td><td>{r['time_ms']:.2f}</td><td>{r['action']}{' *' if r['stopped'] else ''}</td></tr>"
            for n, r in d["results"].items())
        el("debugTable").innerHTML = (
            "<table><tr><th>Aksi NPC</th><th>Skor</th></tr>" + rows + "</table>"
            "<table><tr><th>Algoritma</th><th>Node</th><th>Cut</th><th>ms</th><th>Pilih</th></tr>"
            + cmp_rows + "</table><small>&le; = batas atas (dipangkas alpha-beta); * = early stop aktif</small>")

    def _update_stats(self):
        r = self.last_result
        if r:
            self.stat_expanded.innerText = str(r["expanded"])
            self.stat_cost.innerText = str(r["cost"]) if r["path"] else "tidak ditemukan"
            self.stat_time.innerText = f'{r["time_ms"]:.3f}'
        if self.mode == "battle":
            self.stat_status.innerText = ("Battle selesai. Klik \"Reset Permainan\"." if self.game_over
                                          else "MODE BATTLE - giliran Anda (1=Attack, 2=Defend, 3=Potion)")
        else:
            self.stat_status.innerText = f"Algoritma aktif: {ALGO_LABELS[self.algo]}"


# Jalankan Game
game = Game()
