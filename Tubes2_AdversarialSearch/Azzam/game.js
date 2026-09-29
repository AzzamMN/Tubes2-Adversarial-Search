/**
 * ============================================================
 *  INTERCEPT — Game Engine
 *  Tubes Besar 2: Kecerdasan Buatan — Kelompok 13
 * ============================================================
 *
 *  Mengelola:
 *    - Generasi peta 20×20 dengan jaminan konektivitas (BFS)
 *    - Rendering via HTML5 Canvas (dua lapis: peta + overlay debug)
 *    - Input keyboard (WASD / Arrow Keys)
 *    - Mesin giliran (turn engine): Player → NPC → Player → ...
 *    - Integrasi MinimaxEngine dari minimax.js
 *    - Pembaruan UI panel samping secara real-time
 * ============================================================
 */

// ── Konstanta Tipe Sel ─────────────────────────────────────────
const GRASS = 0;
const WALL  = 1;
const TREE  = 2;
const RIVER = 3;

// ── Konstanta State Permainan ──────────────────────────────────
const STATE_PLAYING     = 'playing';
const STATE_THINKING    = 'thinking';
const STATE_PLAYER_WINS = 'player_wins';
const STATE_NPC_WINS    = 'npc_wins';

// ── Palet Warna ────────────────────────────────────────────────
const COLORS = {
    grass  : '#3d6b50',
    wall   : '#2a2a2a',
    tree   : '#1e4d1e',
    river  : '#1a3d5c',
    grid   : 'rgba(0,0,0,0.12)',
    player : '#4a9eff',
    npc    : '#ff4a4a',
    exit   : '#f1c40f',
};

class Game {
    constructor(canvasId) {
        this.canvas   = document.getElementById(canvasId);
        this.ctx      = this.canvas.getContext('2d');
        this.GRID     = 20;
        this.CS       = 30;   // cell size (px)

        this.canvas.width  = this.GRID * this.CS;
        this.canvas.height = this.GRID * this.CS;

        this.engine = new MinimaxEngine();

        // ── State default ──
        this.algorithm   = 'alphabeta';
        this.depth       = 6;
        this.showHeatMap = true;

        this.gameState      = STATE_PLAYING;
        this.turn           = 0;
        this.log            = [];
        this.lastComparison = null;
        this.heatMap        = null;
        this.pulsePhase     = 0;

        this.init();
        this._bindInput();
        this._loop();
    }

    // ══════════════════════════════════════════════════════════════
    //  Inisialisasi & Generasi Peta
    // ══════════════════════════════════════════════════════════════

    init() {
        this._generateGrid();
        this.player = { x: 1,            y: this.GRID - 2 };
        this.npc    = { x: this.GRID - 2, y: 1            };
        this.exit   = { x: 0,            y: 0             };

        // Pastikan posisi kritis selalu bisa dilewati
        this.grid[this.player.y][this.player.x] = GRASS;
        this.grid[this.npc.y   ][this.npc.x   ] = GRASS;
        this.grid[this.exit.y  ][this.exit.x  ] = GRASS;

        this.engine.setGrid(this.grid);
        this.gameState      = STATE_PLAYING;
        this.turn           = 0;
        this.log            = [];
        this.lastComparison = null;
        this.heatMap        = null;

        this._updateHeatMap();
        this._addLog('Permainan dimulai. Gerakkan Player menuju EXIT ⭐ (pojok kiri atas).');
        this._addLog(`Algoritma NPC: ${this._algoLabel()} | Kedalaman: ${this.depth}`);
        this._updateUI();
    }

    _generateGrid() {
        // Mulai dengan seluruh sel rumput
        this.grid = Array.from({ length: this.GRID }, () =>
            new Array(this.GRID).fill(GRASS)
        );

        // Tempatkan rintangan secara acak dengan generator seed deterministik
        const rng = this._seededRNG(7);
        const DENSITY = 0.24;
        const safe = new Set([
            '0,0', '1,0', '0,1',                           // sekitar EXIT
            `1,${this.GRID-2}`, `1,${this.GRID-1}`,         // sekitar Player start
            `${this.GRID-2},1`, `${this.GRID-1},1`,          // sekitar NPC start
        ]);

        for (let y = 0; y < this.GRID; y++) {
            for (let x = 0; x < this.GRID; x++) {
                if (safe.has(`${x},${y}`)) continue;
                if (rng() < DENSITY) {
                    const r = rng();
                    this.grid[y][x] = r < 0.50 ? WALL : r < 0.80 ? TREE : RIVER;
                }
            }
        }

        // Jamin konektivitas dengan BFS carving
        const pStart = { x: 1,            y: this.GRID - 2 };
        const nStart = { x: this.GRID - 2, y: 1            };
        const exitP  = { x: 0,            y: 0             };

        if (!this._isConnected(pStart, exitP)) this._carvePath(pStart, exitP);
        if (!this._isConnected(nStart, pStart)) this._carvePath(nStart, pStart);
    }

    _seededRNG(seed) {
        let s = seed >>> 0;
        return () => {
            s = (Math.imul(1664525, s) + 1013904223) >>> 0;
            return s / 0xFFFFFFFF;
        };
    }

    _isConnected(a, b) {
        const visited = new Set([`${a.x},${a.y}`]);
        const queue   = [a];
        while (queue.length) {
            const curr = queue.shift();
            if (curr.x === b.x && curr.y === b.y) return true;
            for (const d of [{x:0,y:-1},{x:0,y:1},{x:-1,y:0},{x:1,y:0}]) {
                const nx = curr.x + d.x, ny = curr.y + d.y;
                const key = `${nx},${ny}`;
                if (nx >= 0 && ny >= 0 && nx < this.GRID && ny < this.GRID
                    && this.grid[ny][nx] === GRASS && !visited.has(key)) {
                    visited.add(key);
                    queue.push({ x: nx, y: ny });
                }
            }
        }
        return false;
    }

    _carvePath(from, to) {
        // BFS dari 'from' ke 'to' melalui sel apapun, lalu kosongkan jalur
        const parent = new Map([[ `${from.x},${from.y}`, null ]]);
        const queue  = [from];
        while (queue.length) {
            const curr = queue.shift();
            if (curr.x === to.x && curr.y === to.y) {
                let pos = curr;
                while (pos) {
                    this.grid[pos.y][pos.x] = GRASS;
                    pos = parent.get(`${pos.x},${pos.y}`);
                }
                return;
            }
            for (const d of [{x:0,y:-1},{x:0,y:1},{x:-1,y:0},{x:1,y:0}]) {
                const nx = curr.x + d.x, ny = curr.y + d.y;
                const key = `${nx},${ny}`;
                if (nx >= 0 && ny >= 0 && nx < this.GRID && ny < this.GRID && !parent.has(key)) {
                    parent.set(key, curr);
                    queue.push({ x: nx, y: ny });
                }
            }
        }
    }

    // ══════════════════════════════════════════════════════════════
    //  Input & Turn Management
    // ══════════════════════════════════════════════════════════════

    _bindInput() {
        const DIR_MAP = {
            ArrowUp   : { x:  0, y: -1 }, w: { x:  0, y: -1 }, W: { x:  0, y: -1 },
            ArrowDown : { x:  0, y:  1 }, s: { x:  0, y:  1 }, S: { x:  0, y:  1 },
            ArrowLeft : { x: -1, y:  0 }, a: { x: -1, y:  0 }, A: { x: -1, y:  0 },
            ArrowRight: { x:  1, y:  0 }, d: { x:  1, y:  0 }, D: { x:  1, y:  0 },
        };

        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' || e.key === 'R') { this.reset(); return; }
            if (this.gameState !== STATE_PLAYING) return;

            const dir = DIR_MAP[e.key];
            if (!dir) return;
            e.preventDefault();

            const nx = this.player.x + dir.x;
            const ny = this.player.y + dir.y;

            if (!this.engine.isPassable(nx, ny)) return;

            this.player = { x: nx, y: ny };
            this.turn++;

            // Bug 7 Fix: Update heat map segera setelah player bergerak
            if (this.showHeatMap) this._updateHeatMap();

            // Bug 1 Fix: Cek apakah Player menabrak/berjalan ke NPC
            if (nx === this.npc.x && ny === this.npc.y) {
                this.gameState = STATE_NPC_WINS;
                this._addLog(`💀 Turn ${this.turn}: Player menabrak NPC! NPC MENANG!`);
                this._updateUI();
                return;
            }

            if (nx === this.exit.x && ny === this.exit.y) {
                this.gameState = STATE_PLAYER_WINS;
                this._addLog(`🏆 Turn ${this.turn}: Player mencapai EXIT! PLAYER MENANG!`);
                this._updateUI();
                return;
            }

            this._addLog(`Turn ${this.turn}: Player → (${nx}, ${ny})`);
            this.gameState = STATE_THINKING;
            this._updateUI();

            // Tunda 250ms agar "Berpikir..." sempat terlihat di layar
            setTimeout(() => this._doNPCTurn(), 250);
        });
    }

    _doNPCTurn() {
        if (this.gameState !== STATE_THINKING) return;

        const t0     = performance.now();
        const result = this.engine.getBestMove(
            this.npc, this.player, this.exit,
            this.depth, this.algorithm
        );
        const elapsed = (performance.now() - t0).toFixed(1);

        this.npc            = result.move;
        this.lastComparison = result.comparison;

        this._addLog(
            `Turn ${this.turn}: NPC → (${this.npc.x}, ${this.npc.y}) ` +
            `| ${result.nodes.toLocaleString('id-ID')} nodes | ${elapsed}ms`
        );

        if (this.npc.x === this.player.x && this.npc.y === this.player.y) {
            this.gameState = STATE_NPC_WINS;
            this._addLog(`💀 Turn ${this.turn}: NPC mencegat Player! NPC MENANG!`);
        } else {
            this.gameState = STATE_PLAYING;
        }

        this._updateHeatMap();
        this._updateUI();
    }

    _updateHeatMap() {
        if (this.showHeatMap) {
            this.heatMap = this.engine.generateHeatMap(this.player, this.exit);
        } else {
            this.heatMap = null;
        }
    }

    // ══════════════════════════════════════════════════════════════
    //  Rendering
    // ══════════════════════════════════════════════════════════════

    _loop() {
        this._render();
        requestAnimationFrame(() => this._loop());
    }

    _render() {
        const { ctx, CS, GRID } = this;
        this.pulsePhase += 0.04;

        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // ── Lapisan 1: Sel peta ──
        for (let y = 0; y < GRID; y++) {
            for (let x = 0; x < GRID; x++) {
                ctx.fillStyle = this._cellColor(this.grid[y][x]);
                ctx.fillRect(x * CS, y * CS, CS, CS);
                ctx.strokeStyle = COLORS.grid;
                ctx.lineWidth   = 0.5;
                ctx.strokeRect(x * CS, y * CS, CS, CS);
            }
        }

        // ── Lapisan 2: Heat map overlay (debug) ──
        if (this.heatMap) {
            for (let y = 0; y < GRID; y++) {
                for (let x = 0; x < GRID; x++) {
                    const v = this.heatMap[y][x];
                    if (v === null) continue;
                    const r = Math.round(v * 210);
                    const b = Math.round((1 - v) * 210);
                    ctx.fillStyle = `rgba(${r},40,${b},0.38)`;
                    ctx.fillRect(x * CS, y * CS, CS, CS);
                }
            }
        }

        // ── Lapisan 3: Entitas ──
        this._drawExit();
        this._drawAgent(this.player, COLORS.player, '#2980b9', 'P');
        this._drawAgent(this.npc,    COLORS.npc,    '#c0392b', 'N');

        // ── Lapisan 4: Overlay status ──
        if (this.gameState === STATE_THINKING) this._drawThinking();
        if (this.gameState === STATE_PLAYER_WINS || this.gameState === STATE_NPC_WINS) {
            this._drawGameOver();
        }
    }

    _cellColor(type) {
        return { [GRASS]: COLORS.grass, [WALL]: COLORS.wall,
                 [TREE]:  COLORS.tree,  [RIVER]: COLORS.river }[type] ?? COLORS.grass;
    }

    _drawAgent(pos, fill, stroke, label) {
        const { ctx, CS } = this;
        const cx = pos.x * CS + CS / 2;
        const cy = pos.y * CS + CS / 2;
        const r  = CS * 0.38;

        // Cahaya (glow)
        const g = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r * 2);
        g.addColorStop(0, fill + 'aa');
        g.addColorStop(1, 'transparent');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(cx, cy, r * 2, 0, Math.PI * 2);
        ctx.fill();

        // Lingkaran utama
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fillStyle   = fill;
        ctx.fill();
        ctx.strokeStyle = stroke;
        ctx.lineWidth   = 2;
        ctx.stroke();

        // Label
        ctx.fillStyle    = 'white';
        ctx.font         = `bold ${Math.round(r * 0.9)}px monospace`;
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, cx, cy);
    }

    _drawExit() {
        const { ctx, CS } = this;
        const cx    = this.exit.x * CS + CS / 2;
        const cy    = this.exit.y * CS + CS / 2;
        const pulse = 0.82 + Math.sin(this.pulsePhase) * 0.18;
        const r     = CS * 0.44 * pulse;

        // Cahaya emas
        const g = ctx.createRadialGradient(cx, cy, r * 0.1, cx, cy, r * 2.2);
        g.addColorStop(0, 'rgba(241,196,15,0.95)');
        g.addColorStop(0.5, 'rgba(241,196,15,0.25)');
        g.addColorStop(1, 'transparent');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(cx, cy, r * 2.2, 0, Math.PI * 2);
        ctx.fill();

        // Bintang 5 sudut
        ctx.beginPath();
        for (let i = 0; i < 5; i++) {
            const outer = (i * 4 * Math.PI / 5) - Math.PI / 2;
            const inner = outer + Math.PI / 5;
            const method = i === 0 ? 'moveTo' : 'lineTo';
            ctx[method](cx + r * Math.cos(outer), cy + r * Math.sin(outer));
            ctx.lineTo(cx + r * 0.4 * Math.cos(inner), cy + r * 0.4 * Math.sin(inner));
        }
        ctx.closePath();
        ctx.fillStyle   = COLORS.exit;
        ctx.fill();
        ctx.strokeStyle = '#b7950b';
        ctx.lineWidth   = 1.5;
        ctx.stroke();
    }

    _drawThinking() {
        const { ctx, CS } = this;
        const x = this.npc.x * CS;
        const y = Math.max(0, this.npc.y * CS - 28);
        const dots = '●'.repeat(1 + Math.floor(this.pulsePhase / 1.2) % 3);

        ctx.fillStyle = 'rgba(10,10,20,0.82)';
        ctx.beginPath();
        // Fallback for browsers that don't support roundRect
        if (ctx.roundRect) {
            ctx.roundRect(x - 18, y, 100, 22, 4);
        } else {
            ctx.rect(x - 18, y, 100, 22);
        }
        ctx.fill();

        ctx.fillStyle    = '#f39c12';
        ctx.font         = 'bold 11px monospace';
        ctx.textAlign    = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(`Berpikir ${dots}`, x - 10, y + 11);
    }

    _drawGameOver() {
        const { ctx } = this;
        const win = this.gameState === STATE_PLAYER_WINS;
        ctx.fillStyle = win ? 'rgba(39,174,96,0.88)' : 'rgba(192,57,43,0.88)';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        ctx.fillStyle    = 'white';
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'middle';
        ctx.font         = `bold 34px monospace`;
        ctx.fillText(win ? '🏆  PLAYER MENANG!' : '💀  NPC MENANG!',
                     this.canvas.width / 2, this.canvas.height / 2 - 18);
        ctx.font = '15px monospace';
        ctx.fillText('Tekan  R  untuk main ulang',
                     this.canvas.width / 2, this.canvas.height / 2 + 22);
    }

    // ══════════════════════════════════════════════════════════════
    //  Pembaruan UI Panel
    // ══════════════════════════════════════════════════════════════

    _updateUI() {
        // Status
        const statusMap = {
            [STATE_PLAYING]     : '🎮 Giliran Player',
            [STATE_THINKING]    : '🤖 NPC Berpikir...',
            [STATE_PLAYER_WINS] : '🏆 Player Menang!',
            [STATE_NPC_WINS]    : '💀 NPC Menang!',
        };
        this._setText('game-status', statusMap[this.gameState] ?? '');
        this._setText('turn-counter', this.turn);

        // Tabel perbandingan node
        if (this.lastComparison) {
            const algMap = {
                minimax           : 'minimax',
                alphabeta         : 'alphabeta',
                alphabeta_ordered : 'alphabeta-ordered',
            };
            const maxNodes = Math.max(
                ...Object.values(this.lastComparison).map(d => d.nodes)
            );
            for (const [alg, data] of Object.entries(this.lastComparison)) {
                const id  = algMap[alg];
                const pct = maxNodes > 0 ? (data.nodes / maxNodes) * 100 : 0;
                this._setText(`nodes-${id}`,  data.nodes.toLocaleString('id-ID'));
                this._setText(`time-${id}`,   `${data.time}ms`);
                const bar = document.getElementById(`bar-${id}`);
                if (bar) bar.style.width = `${pct.toFixed(1)}%`;
            }
        }

        // Log permainan
        const logEl = document.getElementById('battle-log');
        if (logEl) {
            logEl.innerHTML = this.log
                .map((msg, i) => `<div class="log-entry${i === 0 ? ' log-latest' : ''}">${msg}</div>`)
                .join('');
        }
    }

    _setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    // ══════════════════════════════════════════════════════════════
    //  API Publik (dipanggil dari HTML)
    // ══════════════════════════════════════════════════════════════

    setAlgorithm(alg) {
        this.algorithm = alg;
        this._addLog(`Algoritma diubah ke: ${this._algoLabel()}`);
        this._updateUI();
    }

    setDepth(d) {
        this.depth = parseInt(d, 10);
        this._setText('depth-display', this.depth);
        this._addLog(`Kedalaman pencarian diubah ke: ${this.depth}`);
        this._updateUI();
    }

    toggleHeatMap() {
        this.showHeatMap = !this.showHeatMap;
        this._updateHeatMap();
        const btn = document.getElementById('debug-toggle');
        if (btn) btn.textContent = `🌡 Heat Map: ${this.showHeatMap ? 'ON' : 'OFF'}`;
    }

    reset() {
        this.init();
    }

    // ── Helpers ──────────────────────────────────────────────────

    _addLog(msg) {
        const t = new Date().toLocaleTimeString('id-ID', {
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
        this.log.unshift(`[${t}] ${msg}`);
        if (this.log.length > 25) this.log.pop();
    }

    _algoLabel() {
        return {
            minimax           : 'Pure Minimax',
            alphabeta         : 'Alpha-Beta Pruning',
            alphabeta_ordered : 'AB + Move Ordering',
        }[this.algorithm] ?? this.algorithm;
    }
}

// ── Bootstrap ─────────────────────────────────────────────────
let game;
document.addEventListener('DOMContentLoaded', () => {
    game = new Game('gameCanvas');
});
