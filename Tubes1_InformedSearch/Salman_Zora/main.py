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
# 5. CLASS GAME
# =====================================================================
class Game:
    KEY_MAP = {
        "ArrowUp": (0, -1), "w": (0, -1), "W": (0, -1),
        "ArrowDown": (0, 1), "s": (0, 1), "S": (0, 1),
        "ArrowLeft": (-1, 0), "a": (-1, 0), "A": (-1, 0),
        "ArrowRight": (1, 0), "d": (1, 0), "D": (1, 0),
    }

    START_PLAYER = (17, 2)
    START_NPC = (2, 18)

    def __init__(self):
        self.grid = GridMap(MAP_DATA)
        self.player = self.START_PLAYER
        self.npc = self.START_NPC
        self.algo = "astar_manhattan"
        self.last_result = None
        self.game_over = False

        self.canvas = document.getElementById("gameCanvas")
        self.ctx = self.canvas.getContext("2d")
        self.stat_expanded = document.getElementById("statExpanded")
        self.stat_cost = document.getElementById("statCost")
        self.stat_time = document.getElementById("statTime")
        self.stat_status = document.getElementById("statStatus")

        self._bind_events()
        self.recompute_npc_path()
        self.render()

    def _bind_events(self):
        self._keydown_proxy = create_proxy(self.on_keydown)
        document.addEventListener("keydown", self._keydown_proxy)

        select = document.getElementById("algoSelect")
        self._select_proxy = create_proxy(self.on_algo_change)
        select.addEventListener("change", self._select_proxy)

        btn = document.getElementById("resetBtn")
        self._reset_proxy = create_proxy(self.on_reset)
        btn.addEventListener("click", self._reset_proxy)

    def on_algo_change(self, event):
        self.algo = event.target.value
        self.recompute_npc_path()
        self.render()

    def on_reset(self, event=None):
        self.player = self.START_PLAYER
        self.npc = self.START_NPC
        self.game_over = False
        self.recompute_npc_path()
        self.render()

    def on_keydown(self, event):
        if self.game_over:
            return
        key = event.key
        if key not in self.KEY_MAP:
            return
        event.preventDefault()

        dx, dy = self.KEY_MAP[key]
        target = (self.player[0] + dx, self.player[1] + dy)
        if self.grid.walkable(target):
            self.player = target

        # 1. Gerakkan NPC menyusuri jalur
        self.step_npc()
        self.check_capture()

        # 2. Hitung ulang jalur & render overlay terbaru
        self.recompute_npc_path()
        self.render()

    def recompute_npc_path(self):
        heuristic_fn = HEURISTICS[self.algo]
        self.last_result = Pathfinding.search(self.grid, self.npc, self.player, heuristic_fn)

    def step_npc(self):
        result = self.last_result
        if result and result["path"] and len(result["path"]) > 1:
            self.npc = result["path"][1]

    def check_capture(self):
        if self.npc == self.player:
            self.game_over = True

    def render(self):
        ctx = self.ctx
        ctx.clearRect(0, 0, self.canvas.width, self.canvas.height)

        for y in range(self.grid.height):
            for x in range(self.grid.width):
                t = self.grid.tile((x, y))
                ctx.fillStyle = TILE_COLORS.get(t, "#000000")
                ctx.fillRect(x * TILE, y * TILE, TILE, TILE)
                ctx.strokeStyle = "rgba(0,0,0,0.18)"
                ctx.strokeRect(x * TILE, y * TILE, TILE, TILE)

        r = self.last_result
        if r:
            ctx.fillStyle = "rgba(255,60,60,0.38)"
            for (x, y) in r["closed"]:
                ctx.fillRect(x * TILE, y * TILE, TILE, TILE)

            ctx.fillStyle = "rgba(255,220,60,0.40)"
            for (x, y) in r["open"]:
                ctx.fillRect(x * TILE, y * TILE, TILE, TILE)

            if r["path"]:
                ctx.fillStyle = "rgba(60,255,120,0.6)"
                for (x, y) in r["path"]:
                    ctx.fillRect(x * TILE, y * TILE, TILE, TILE)

        self._draw_entity(self.npc, "#ff5470")
        self._draw_entity(self.player, "#4fc3f7")

        self._update_stats()

    def _draw_entity(self, pos, color):
        ctx = self.ctx
        x, y = pos
        cx = x * TILE + TILE / 2
        cy = y * TILE + TILE / 2
        ctx.beginPath()
        ctx.arc(cx, cy, TILE * 0.34, 0, 2 * math.pi)
        ctx.fillStyle = color
        ctx.fill()
        ctx.lineWidth = 2
        ctx.strokeStyle = "#0d1117"
        ctx.stroke()

    def _update_stats(self):
        r = self.last_result
        if not r:
            return
        self.stat_expanded.innerText = str(r["expanded"])
        self.stat_cost.innerText = str(r["cost"]) if r["path"] else "tidak ditemukan"
        self.stat_time.innerText = f'{r["time_ms"]:.3f}'

        if self.game_over:
            self.stat_status.innerText = "NPC menangkap Player! Klik \"Reset Permainan\" untuk main lagi."
        else:
            self.stat_status.innerText = f"Algoritma aktif: {ALGO_LABELS[self.algo]}"


# Jalankan Game
game = Game()