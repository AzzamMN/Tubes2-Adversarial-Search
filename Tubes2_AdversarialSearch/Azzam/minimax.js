/**
 * ============================================================
 *  INTERCEPT — Adversarial Search Engine
 *  Tubes Besar 2: Kecerdasan Buatan — Kelompok 13
 * ============================================================
 *
 *  Implementasi tiga varian algoritma Adversarial Search:
 *    1. Pure Minimax          — ekspansi pohon penuh, O(b^d)
 *    2. Alpha-Beta Pruning    — pemangkasan α-β, ~O(b^(d/2))
 *    3. AB + Move Ordering    — pemangkasan + pengurutan heuristik
 *
 *  Konsep permainan INTERCEPT:
 *    - NPC (Maximizer) mencoba mencegat Player sebelum Player
 *      mencapai EXIT di pojok kiri atas peta.
 *    - Player (Minimizer) diasumsikan bermain secara optimal
 *      di dalam pohon permainan, sehingga NPC harus memperhitungkan
 *      respons terbaik Player pada setiap simpul MIN.
 *    - Gerakan tunggal NPC dihitung oleh Minimax — bukan hanya
 *      fase battle, melainkan setiap langkah fisik di grid.
 * ============================================================
 */

class MinimaxEngine {
    constructor() {
        this.GRID_SIZE = 20;
        this.grid = null;
        // Konstanta tipe sel — disinkronkan dengan game.js
        this.GRASS = 0;
        this.WALL  = 1;
        this.TREE  = 2;
        this.RIVER = 3;
    }

    /** Suntikkan referensi grid dari Game dan prekomputasi jarak ke Exit */
    setGrid(grid, exitPos) {
        this.grid = grid;
        if (exitPos) {
            this._precomputeExitDistances(exitPos);
        }
    }

    _precomputeExitDistances(exitPos) {
        this.distMap = Array.from({ length: this.GRID_SIZE }, () =>
            new Array(this.GRID_SIZE).fill(Infinity)
        );
        const queue = [exitPos];
        this.distMap[exitPos.y][exitPos.x] = 0;
        
        while (queue.length > 0) {
            const curr = queue.shift();
            const d = this.distMap[curr.y][curr.x];
            
            for (const dir of [{x:0,y:-1},{x:0,y:1},{x:-1,y:0},{x:1,y:0}]) {
                const nx = curr.x + dir.x;
                const ny = curr.y + dir.y;
                if (this.isPassable(nx, ny) && this.distMap[ny][nx] === Infinity) {
                    this.distMap[ny][nx] = d + 1;
                    queue.push({ x: nx, y: ny });
                }
            }
        }
    }

    // ─── Utilitas Grid ──────────────────────────────────────────

    isValid(x, y) {
        return x >= 0 && y >= 0 && x < this.GRID_SIZE && y < this.GRID_SIZE;
    }

    isPassable(x, y) {
        if (!this.isValid(x, y)) return false;
        return this.grid[y][x] === this.GRASS;
    }

    /**
     * Kembalikan daftar sel yang dapat dituju dari posisi pos.
     * Hanya sel rumput (GRASS) yang diizinkan.
     */
    getNeighbors(pos) {
        const DIRS = [
            { x:  0, y: -1 },  // Atas
            { x:  0, y:  1 },  // Bawah
            { x: -1, y:  0 },  // Kiri
            { x:  1, y:  0 },  // Kanan
        ];
        const result = [];
        for (const d of DIRS) {
            const nx = pos.x + d.x;
            const ny = pos.y + d.y;
            if (this.isPassable(nx, ny)) {
                result.push({ x: nx, y: ny });
            }
        }
        return result;
    }

    manhattan(a, b) {
        return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
    }

    // ─── Fungsi Evaluasi Heuristik ───────────────────────────────

    /**
     * evaluate(npc, player, exit) → number
     *
     * Nilai positif = keunggulan NPC (Maximizer)
     * Nilai negatif = keunggulan Player (Minimizer)
     *
     * Empat komponen evaluasi:
     *  (1) Kedekatan NPC → Player   : semakin dekat, semakin baik bagi NPC
     *  (2) Jarak Player → EXIT      : semakin jauh, semakin baik bagi NPC
     *  (3) Bonus posisi blokade     : NPC mendapat bonus besar jika berada
     *                                 di antara Player dan EXIT
     *  (4) Pembatasan mobilitas     : semakin sedikit pilihan Player, semakin baik
     */
    evaluate(npc, player, exit) {
        // Terminal cepat (tanpa rekursi)
        if (npc.x === player.x && npc.y === player.y) return  10000;
        if (player.x === exit.x  && player.y === exit.y)  return -10000;

        // Bug 8 Fix: Gunakan BFS (obstacle-aware) distance untuk path ke Exit,
        // bukan manhattan, agar NPC tidak terkecoh oleh tembok panjang.
        const distNP  = this.manhattan(npc, player);      
        const distPE  = this.distMap[player.y][player.x]; // Jarak sesungguhnya ke Exit
        const distNE  = this.distMap[npc.y][npc.x];       // Jarak sesungguhnya ke Exit

        // Komponen (3): bonus blokade geometris
        // NPC "memblokir" jika lebih dekat ke EXIT daripada Player,
        // dan berada di rute terdekat Player → EXIT (toleransi ±2 langkah)
        const isOnPath     = (distNP + distNE) <= (distPE + 2);
        const hasAdvantage = distNE < distPE;
        const blockBonus   = (isOnPath && hasAdvantage)
                             ? Math.max(0, (distPE - distNE)) * 18
                             : (hasAdvantage ? 10 : 0);

        // Komponen (4): mobilitas Player
        const mobility = this.getNeighbors(player).length;

        return (15 - distNP) * 12    // (1) NPC ingin dekat Player
             + distPE        *  8    // (2) NPC ingin Player jauh dari Exit
             + blockBonus            // (3) Bonus blokade
             - mobility      *  5;   // (4) Kurangi mobilitas Player
    }

    // ─── Algoritma 1: Pure Minimax ───────────────────────────────

    /**
     * minimax(npc, player, exit, depth, isMaximizing, nodesRef)
     *
     * Menelusuri pohon permainan secara exhaustive tanpa pruning.
     * Setiap simpul dihitung — tidak ada yang dipotong.
     * Kompleksitas: O(b^d) di mana b ≈ 4 (4-arah), d = kedalaman.
     *
     * nodesRef.count diincrement setiap kali fungsi dipanggil,
     * sehingga hitungan node yang di-expand dapat dibandingkan.
     */
    minimax(npc, player, exit, depth, isMaximizing, nodesRef) {
        nodesRef.count++;

        // State terminal — kembalikan nilai dengan bonus kedalaman
        // agar Minimax memilih kemenangan SECEPAT mungkin
        if (npc.x === player.x && npc.y === player.y) return  10000 + depth;
        if (player.x === exit.x  && player.y === exit.y)  return -10000 - depth;
        if (depth === 0) return this.evaluate(npc, player, exit);

        if (isMaximizing) {
            // NPC memilih gerakan dengan nilai tertinggi
            const moves = this.getNeighbors(npc);
            if (moves.length === 0) return this.evaluate(npc, player, exit);

            let maxScore = -Infinity;
            for (const move of moves) {
                const score = this.minimax(move, player, exit, depth - 1, false, nodesRef);
                if (score > maxScore) maxScore = score;
            }
            return maxScore;

        } else {
            // Player memilih gerakan dengan nilai terendah (bermain optimal melawan NPC)
            const moves = this.getNeighbors(player);
            if (moves.length === 0) return this.evaluate(npc, player, exit);

            let minScore = Infinity;
            for (const move of moves) {
                const score = this.minimax(npc, move, exit, depth - 1, true, nodesRef);
                if (score < minScore) minScore = score;
            }
            return minScore;
        }
    }

    // ─── Algoritma 2: Alpha-Beta Pruning ─────────────────────────

    /**
     * alphabeta(npc, player, exit, depth, alpha, beta, isMaximizing, nodesRef)
     *
     * Sama dengan Minimax, namun memangkas cabang yang terbukti
     * tidak akan mengubah keputusan akhir.
     *
     * α (alpha): nilai terbaik yang sudah dijamin oleh Maximizer (NPC)
     * β (beta) : nilai terbaik yang sudah dijamin oleh Minimizer (Player)
     *
     * β-cutoff (pada MAX node): jika score ≥ β, Minimizer tidak akan
     *   pernah memilih jalur ini → hentikan ekspansi.
     * α-cutoff (pada MIN node): jika score ≤ α, Maximizer tidak akan
     *   pernah memilih jalur ini → hentikan ekspansi.
     *
     * Kompleksitas ideal (dengan pengurutan sempurna): O(b^(d/2)).
     */
    alphabeta(npc, player, exit, depth, alpha, beta, isMaximizing, nodesRef) {
        nodesRef.count++;

        if (npc.x === player.x && npc.y === player.y) return  10000 + depth;
        if (player.x === exit.x  && player.y === exit.y)  return -10000 - depth;
        if (depth === 0) return this.evaluate(npc, player, exit);

        if (isMaximizing) {
            const moves = this.getNeighbors(npc);
            if (moves.length === 0) return this.evaluate(npc, player, exit);

            let maxScore = -Infinity;
            for (const move of moves) {
                const score = this.alphabeta(move, player, exit, depth - 1, alpha, beta, false, nodesRef);
                if (score > maxScore) maxScore = score;
                if (maxScore > alpha) alpha = maxScore;
                if (beta <= alpha) break; // β-cutoff: Minimizer tidak akan memilih jalur ini
            }
            return maxScore;

        } else {
            const moves = this.getNeighbors(player);
            if (moves.length === 0) return this.evaluate(npc, player, exit);

            let minScore = Infinity;
            for (const move of moves) {
                const score = this.alphabeta(npc, move, exit, depth - 1, alpha, beta, true, nodesRef);
                if (score < minScore) minScore = score;
                if (minScore < beta) beta = minScore;
                if (beta <= alpha) break; // α-cutoff: Maximizer tidak akan memilih jalur ini
            }
            return minScore;
        }
    }

    // ─── Algoritma 3: AB + Move Ordering ─────────────────────────

    /**
     * Pengurutan Langkah (Move Ordering):
     * Sebelum mengevaluasi, urutkan langkah-langkah yang tersedia
     * berdasarkan perkiraan nilai heuristik.
     *
     * - Pada giliran NPC (MAX): urutkan langkah dari yang PALING DEKAT ke Player
     *   (kemungkinan langkah terbaik dievaluasi lebih dulu → alpha meningkat cepat
     *   → lebih banyak β-cutoff).
     * - Pada giliran Player (MIN): urutkan langkah dari yang PALING DEKAT ke EXIT
     *   (kemungkinan langkah terbaik Player dievaluasi lebih dulu → beta menurun cepat
     *   → lebih banyak α-cutoff).
     *
     * Ini adalah teknik standar yang mengangkat efektivitas Alpha-Beta dari
     * O(b^d) mendekati O(b^(d/2)) secara konsisten.
     */
    _orderForMax(moves, target) {
        // Urutkan ascending berdasarkan jarak ke target (yang terdekat lebih dulu)
        return moves.slice().sort((a, b) =>
            this.manhattan(a, target) - this.manhattan(b, target)
        );
    }

    _orderForMin(moves, target) {
        return moves.slice().sort((a, b) =>
            this.manhattan(a, target) - this.manhattan(b, target)
        );
    }

    alphabetaOrdered(npc, player, exit, depth, alpha, beta, isMaximizing, nodesRef) {
        nodesRef.count++;

        if (npc.x === player.x && npc.y === player.y) return  10000 + depth;
        if (player.x === exit.x  && player.y === exit.y)  return -10000 - depth;
        if (depth === 0) return this.evaluate(npc, player, exit);

        if (isMaximizing) {
            // Urutkan: NPC lebih dulu coba gerakan yang mendekatkan ke Player
            const moves = this._orderForMax(this.getNeighbors(npc), player);
            if (moves.length === 0) return this.evaluate(npc, player, exit);

            let maxScore = -Infinity;
            for (const move of moves) {
                const score = this.alphabetaOrdered(move, player, exit, depth - 1, alpha, beta, false, nodesRef);
                if (score > maxScore) maxScore = score;
                if (maxScore > alpha) alpha = maxScore;
                if (beta <= alpha) break;
            }
            return maxScore;

        } else {
            // Urutkan: Player lebih dulu coba gerakan yang mendekatkan ke EXIT
            const moves = this._orderForMin(this.getNeighbors(player), exit);
            if (moves.length === 0) return this.evaluate(npc, player, exit);

            let minScore = Infinity;
            for (const move of moves) {
                const score = this.alphabetaOrdered(npc, move, exit, depth - 1, alpha, beta, true, nodesRef);
                if (score < minScore) minScore = score;
                if (minScore < beta) beta = minScore;
                if (beta <= alpha) break;
            }
            return minScore;
        }
    }

    // ─── Dispatcher Utama ────────────────────────────────────────

    /**
     * getBestMove(npcPos, playerPos, exitPos, depth, algorithm)
     *
     * Menghitung langkah terbaik NPC menggunakan algoritma yang dipilih.
     * Sekaligus menjalankan ketiga algoritma secara paralel untuk
     * keperluan perbandingan eksperimental di laporan.
     *
     * Returns: { move: {x,y}, nodes: number, comparison: {...} }
     */
    getBestMove(npcPos, playerPos, exitPos, depth, algorithm) {
        const candidateMoves = this.getNeighbors(npcPos);
        if (candidateMoves.length === 0) {
            return { move: npcPos, nodes: 0, comparison: null };
        }

        // Jalankan perbandingan (sekaligus mendapatkan langkah terbaik)
        const comparison = this._compareAll(npcPos, playerPos, exitPos, depth, algorithm);

        // Map nama algoritma ke hasil
        const activeKey = algorithm; // 'minimax', 'alphabeta', atau 'alphabeta_ordered'
        
        return {
            move       : comparison[activeKey].bestMove || candidateMoves[0],
            nodes      : comparison[activeKey].nodes,
            comparison : comparison,
        };
    }

    /**
     * Jalankan ketiga algoritma dari posisi yang sama, catat jumlah node
     * dan waktu komputasi untuk ditampilkan di panel perbandingan.
     */
    _compareAll(npcPos, playerPos, exitPos, depth, selectedAlgorithm) {
        const algorithms = ['minimax', 'alphabeta', 'alphabeta_ordered'];
        const result = {};

        for (const alg of algorithms) {
            const ref = { count: 0 };
            const t0  = performance.now();

            let candidates = this.getNeighbors(npcPos);
            
            // Bug 3 Fix: Urutkan kandidat di level root untuk AB Ordered
            if (alg === 'alphabeta_ordered') {
                candidates = this._orderForMax(candidates, playerPos);
            }

            let bestMove  = candidates[0];
            let bestScore = -Infinity;
            let alpha     = -Infinity; // Bug 2 Fix: Inisialisasi alpha di root
            const beta    = Infinity;

            // Bug 5 Fix: Skip Pure Minimax di kedalaman > 6 jika tidak dipilih aktif,
            // untuk mencegah UI freeze (browser lag karena mengekspansi 65k+ node secara sinkron)
            if (alg === 'minimax' && depth > 6 && selectedAlgorithm !== 'minimax') {
                result[alg] = { bestMove: null, nodes: "Skipped", time: "-" };
                continue;
            }

            for (const move of candidates) {
                const sub = { count: 0 };
                let score;

                if (alg === 'minimax') {
                    score = this.minimax(move, playerPos, exitPos, depth - 1, false, sub);
                } else if (alg === 'alphabeta') {
                    score = this.alphabeta(move, playerPos, exitPos, depth - 1, alpha, beta, false, sub);
                } else {
                    score = this.alphabetaOrdered(move, playerPos, exitPos, depth - 1, alpha, beta, false, sub);
                }

                ref.count += sub.count; // Bug 6 Fix: Jangan double-count root node

                if (score > bestScore) {
                    bestScore = score;
                    bestMove  = move;
                }
                
                // Bug 2 Fix: Update alpha dari hasil evaluasi branch root
                if (bestScore > alpha) {
                    alpha = bestScore;
                }
            }

            result[alg] = {
                bestMove: bestMove,
                nodes: ref.count + 1, // +1 untuk root node itu sendiri
                time : (performance.now() - t0).toFixed(1),
            };
        }

        return result;
    }

    // ─── Debug Heat Map ──────────────────────────────────────────

    /**
     * generateHeatMap(playerPos, exitPos) → number[][] | null[][]
     *
     * Evaluasi setiap sel di peta seolah-olah NPC berada di sel tersebut.
     * Hasilnya dinormalisasi ke rentang [0, 1] untuk visualisasi warna:
     *   1.0 → merah penuh (keunggulan NPC sangat tinggi)
     *   0.0 → biru penuh (keunggulan Player sangat tinggi)
     */
    generateHeatMap(playerPos, exitPos) {
        const raw = [];
        let minVal =  Infinity;
        let maxVal = -Infinity;

        for (let y = 0; y < this.GRID_SIZE; y++) {
            raw.push([]);
            for (let x = 0; x < this.GRID_SIZE; x++) {
                if (!this.isPassable(x, y)) {
                    raw[y].push(null);
                } else {
                    const val = this.evaluate({ x, y }, playerPos, exitPos);
                    raw[y].push(val);
                    if (val < minVal) minVal = val;
                    if (val > maxVal) maxVal = val;
                }
            }
        }

        // Normalisasi ke [0, 1]
        const range = (maxVal - minVal) || 1;
        return raw.map(row =>
            row.map(v => v === null ? null : (v - minVal) / range)
        );
    }
}
