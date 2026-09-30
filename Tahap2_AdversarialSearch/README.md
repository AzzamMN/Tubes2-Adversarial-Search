# Tahap 2: Adversarial Search (Merged / Ultimate Version)

Repositori tunggal ini merupakan **gabungan dari seluruh karya anggota Kelompok 13** (Azzam, Salman, Zora) untuk Tahap 2 (Adversarial Search).

## 🌟 Fitur Gabungan (Ultimate Engine)
* **Base Engine (Azzam):** Game Grid Interaktif (*INTERCEPT*) dengan HTML5 Canvas, pencarian BFS terintegrasi untuk jarak aman rintangan, perbandingan algoritma live, penghitungan jumlah ekspansi *node*, dan UI Panel.
* **Gaya Bermain NPC / Evaluation Heuristics (Gabungan Salman & Zora):**
  * **Aggressive (Salman):** NPC berfokus sepenuhnya untuk menyerang/mengejar (jarak ke Player) dengan mengabaikan seberapa dekat Player dengan jalan keluar (EXIT).
  * **Defensive (Zora):** NPC berfokus murni pada menjaga jalur EXIT dan mengutamakan rute yang menghalangi laju target (blokade pertahanan).
  * **Balanced (Azzam):** Evaluasi berbobot dinamis antara jarak ke target, posisi EXIT target, blokade geometris, dan pembatasan mobilitas.
* **Algoritma Tambahan Expectimax (Zora):** Asumsi probabilistik bahwa Player tidak selalu bergerak optimal (mengurangi pesimisme murni dari fungsi Minimax).

## 🚀 Algoritma yang Disertakan
1. **Pure Minimax**: Tree ditelusuri sepenuhnya, memakan waktu lama pada kedalaman (depth) > 4.
2. **Alpha-Beta Pruning**: Menghilangkan cabang pencarian yang secara matematis tidak akan dipilih, menjamin kecepatan ekstra tanpa mengorbankan keakuratan hasil (optimal).
3. **Alpha-Beta + Move Ordering**: Secara krusial mengurutkan percabangan terdekat (heuristik root & intermediate sort) terlebih dahulu untuk memicu *pruning* (pemangkasan alpha/beta) lebih awal!
4. **Expectimax**: Algoritma yang menggunakan *Chance Node* untuk menghitung nilai harapan (*expected value*) Player, mensimulasikan giliran target yang non-deterministik/acak.

## 🕹️ Cara Menjalankan
1. Cukup buka `index.html` pada browser Anda (Chrome/Firefox/Edge). *Tidak butuh server.*
2. Gunakan **W, A, S, D** atau **Tombol Panah** untuk menggerakkan Player (Kotak Biru). Tujuan Anda adalah titik kuning (Kiri Atas).
3. Anda dapat bereksperimen dengan mengubah **Algoritma**, memilih **Gaya Bermain NPC**, maupun **Kedalaman Pencarian (Depth)** langsung dari Panel Kanan UI.
4. Jangan lupa coba hidupkan fitur *Heat Map* untuk visualisasi jarak geometrik.
