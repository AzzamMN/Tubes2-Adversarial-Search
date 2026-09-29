# Tubes Tahap 1: Informed Search (UCS & A*)

Repositori ini memuat implementasi *bare-metal* dari algoritma Uniform Cost Search (UCS) dan A* Search untuk penyelesaian Tugas Besar Tahap 1. Simulasi dibangun murni menggunakan JavaScript dan HTML5 Canvas tanpa *game engine* pihak ketiga, untuk mendemonstrasikan mekanika penelusuran graf dan evaluasi heuristik secara transparan.

## Struktur Berkas
- `index.html`: Entry point, antarmuka pengguna, dan visualisasi Canvas.
- `PriorityQueue.js`: Implementasi *Binary Min-Heap* kustom. Memastikan operasi *enqueue/dequeue* berjalan pada kompleksitas waktu $O(\log N)$ untuk menghindari *bottleneck* $O(N \log N)$ dari penggunaan `Array.sort()`.
- `agent.js`: Memuat definisi *State-Space*, matriks biaya transisi ($c(n, a, n')$), fungsi heuristik ($h(n)$), dan logika algoritma pencarian.

## Konfigurasi Cost Environment
- **Ground (Tanah)**: Cost 1
- **Tree (Pohon)**: Cost 3
- **River (Sungai)**: Cost 5
- **Wall (Tembok)**: Imposibel ($\infty$)

## Fungsi Heuristik yang Dievaluasi
1. **UCS ($h(n) = 0$)**: Basis kontrol eksplorasi radial.
2. **A* Manhattan Distance**: Admissible untuk pergerakan 4-arah (ortogonal).
3. **A* Euclidean**: Admissible, perhitungan garis lurus.
4. **A* Euclidean Squared**: Inadmissible (sengaja melakukan *overestimate* sebagai bahan evaluasi batas teorema).

## Cara Menjalankan
Buka berkas `index.html` pada peramban web (*browser*). Klik di mana saja pada kanvas untuk mengubah target (*player*), dan pilih algoritma pada menu *dropdown* untuk membandingkan jumlah *Nodes Expanded*.
