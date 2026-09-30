const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const COLS = 40;
const ROWS = 30;
const CELL_SIZE = 20;

// Definisi Cost Matriks
const TERRAIN = {
    GROUND: { id: 0, cost: 1, color: '#333' },
    TREE: { id: 1, cost: 3, color: '#2E8B57' },
    RIVER: { id: 2, cost: 5, color: '#1E90FF' },
    WALL: { id: 3, cost: Infinity, color: '#8B4513' }
};

let grid = [];
let player = { x: 35, y: 25 };
let npc = { x: 2, y: 2 };
let path = [];
let expandedNodes = [];

// Fungsi Heuristik Matematik
function heuristic(x1, y1, x2, y2, type) {
    if (type === 'UCS') return 0;
    
    const dx = Math.abs(x1 - x2);
    const dy = Math.abs(y1 - y2);
    
    if (type === 'A*_Manhattan') {
        // Admissible untuk gerakan 4-arah
        return dx + dy;
    } else if (type === 'A*_Euclidean') {
        // Admissible (Garis lurus <= Jarak aktual grid)
        return Math.sqrt(dx * dx + dy * dy);
    } else if (type === 'A*_Bad') {
        // INADMISSIBLE: Menghasilkan nilai overestimate kuadratik, 
        // merusak Teorema Optimalitas A* dan memicu jebakan sub-optimal.
        return dx * dx + dy * dy; 
    }
    return 0;
}

function generateMap() {
    grid = [];
    for (let y = 0; y < ROWS; y++) {
        let row = [];
        for (let x = 0; x < COLS; x++) {
            // Generasi prosedural sederhana
            let rand = Math.random();
            if (rand < 0.15) row.push(TERRAIN.WALL.id);
            else if (rand < 0.25) row.push(TERRAIN.TREE.id);
            else if (rand < 0.35) row.push(TERRAIN.RIVER.id);
            else row.push(TERRAIN.GROUND.id);
        }
        grid.push(row);
    }
    // Pastikan spawn point aman
    grid[npc.y][npc.x] = TERRAIN.GROUND.id;
    grid[player.y][player.x] = TERRAIN.GROUND.id;
    
    path = [];
    expandedNodes = [];
    draw();
}

function getNeighbors(x, y) {
    const dirs = [[0, -1], [1, 0], [0, 1], [-1, 0]]; // Atas, Kanan, Bawah, Kiri
    let neighbors = [];
    for (let d of dirs) {
        let nx = x + d[0], ny = y + d[1];
        if (nx >= 0 && nx < COLS && ny >= 0 && ny < ROWS) {
            let t_id = grid[ny][nx];
            let cost = 1;
            if (t_id === TERRAIN.TREE.id) cost = 3;
            else if (t_id === TERRAIN.RIVER.id) cost = 5;
            else if (t_id === TERRAIN.WALL.id) cost = Infinity;
            
            if (cost !== Infinity) {
                neighbors.push({ x: nx, y: ny, cost: cost });
            }
        }
    }
    return neighbors;
}

function searchPath(algoType) {
    let t0 = performance.now();
    let pq = new PriorityQueue();
    let startNode = { x: npc.x, y: npc.y, g: 0, f: 0, parent: null };
    
    pq.enqueue(startNode, 0);
    
    let cameFrom = new Map();
    let costSoFar = new Map();
    let startKey = `${npc.x},${npc.y}`;
    costSoFar.set(startKey, 0);
    
    expandedNodes = [];
    let foundGoal = null;

    while (!pq.isEmpty()) {
        let current = pq.dequeue().element;
        let currKey = `${current.x},${current.y}`;
        
        expandedNodes.push({x: current.x, y: current.y});

        if (current.x === player.x && current.y === player.y) {
            foundGoal = current;
            break;
        }

        let neighbors = getNeighbors(current.x, current.y);
        for (let next of neighbors) {
            let newCost = costSoFar.get(currKey) + next.cost;
            let nextKey = `${next.x},${next.y}`;
            
            if (!costSoFar.has(nextKey) || newCost < costSoFar.get(nextKey)) {
                costSoFar.set(nextKey, newCost);
                let h = heuristic(next.x, next.y, player.x, player.y, algoType);
                let priority = newCost + h; // f(n) = g(n) + h(n)
                
                let nextNode = { x: next.x, y: next.y, g: newCost, f: priority, parent: current };
                pq.enqueue(nextNode, priority);
                cameFrom.set(nextKey, current);
            }
        }
    }

    let t1 = performance.now();
    
    path = [];
    let finalCost = 0;
    if (foundGoal) {
        finalCost = foundGoal.g;
        let curr = foundGoal;
        while (curr.parent !== null) {
            path.push({x: curr.x, y: curr.y});
            curr = curr.parent;
        }
        path.reverse();
    }

    // Update UI Stats
    document.getElementById('stats').innerHTML = 
        `Nodes Expanded: <b>${expandedNodes.length}</b><br>` +
        `Path Cost (g(n)): <b>${finalCost}</b><br>` +
        `Execution Time: <b>${(t1 - t0).toFixed(2)} ms</b>`;
        
    return path;
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 1. Draw Grid
    for (let y = 0; y < ROWS; y++) {
        for (let x = 0; x < COLS; x++) {
            let t_id = grid[y][x];
            if (t_id === TERRAIN.GROUND.id) ctx.fillStyle = TERRAIN.GROUND.color;
            else if (t_id === TERRAIN.TREE.id) ctx.fillStyle = TERRAIN.TREE.color;
            else if (t_id === TERRAIN.RIVER.id) ctx.fillStyle = TERRAIN.RIVER.color;
            else if (t_id === TERRAIN.WALL.id) ctx.fillStyle = TERRAIN.WALL.color;
            
            ctx.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
            ctx.strokeStyle = '#222';
            ctx.strokeRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
        }
    }

    // 2. Draw Debug Overlay (Expanded Nodes)
    if (document.getElementById('debugOverlay').checked) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        for (let node of expandedNodes) {
            ctx.fillRect(node.x * CELL_SIZE, node.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
        }
    }

    // 3. Draw Path
    ctx.fillStyle = 'rgba(255, 0, 255, 0.6)';
    for (let node of path) {
        ctx.fillRect(node.x * CELL_SIZE, node.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
    }

    // 4. Draw Player & NPC
    ctx.fillStyle = '#FFFF00'; // Player
    ctx.fillRect(player.x * CELL_SIZE, player.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
    
    ctx.fillStyle = '#FF0000'; // NPC
    ctx.fillRect(npc.x * CELL_SIZE, npc.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
}

function runAgent() {
    let algo = document.getElementById('algoSelect').value;
    searchPath(algo);
    draw();
}

// Click to move player
canvas.addEventListener('mousedown', function(e) {
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / CELL_SIZE);
    const y = Math.floor((e.clientY - rect.top) / CELL_SIZE);
    
    if (x >= 0 && x < COLS && y >= 0 && y < ROWS && grid[y][x] !== TERRAIN.WALL.id) {
        player.x = x;
        player.y = y;
        runAgent(); // Auto run agent upon move
    }
});

// Fitur Gabungan: Chase Mode (terinspirasi dari versi PyScript Salman & Zora)
let chaseInterval = null;
let isChasing = false;

function toggleChase() {
    isChasing = !isChasing;
    const btn = document.getElementById('chaseBtn');
    if (isChasing) {
        btn.innerText = "🛑 Stop Chase";
        btn.classList.add('active');
        chaseInterval = setInterval(() => {
            if (path.length > 0) {
                // NPC melangkah ke node pertama dari path
                const nextStep = path[0];
                npc.x = nextStep.x;
                npc.y = nextStep.y;
                runAgent(); // Hitung ulang path setelah bergerak
                
                if (npc.x === player.x && npc.y === player.y) {
                    toggleChase(); // Berhenti jika tertangkap
                    alert("Player tertangkap!");
                }
            }
        }, 300); // Kecepatan NPC (300ms per langkah)
    } else {
        btn.innerText = "🏃‍♂️ Start Chase Mode";
        btn.classList.remove('active');
        clearInterval(chaseInterval);
    }
}

// Initialize
generateMap();
