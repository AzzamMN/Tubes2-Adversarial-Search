# Tahap 1: Informed Search (Merged / Ultimate Version)

Repositori tunggal ini merupakan gabungan terbaik (Ultimate Version) dari implementasi seluruh anggota kelompok 13 untuk Tahap 1 (Informed Search).

## 🌟 Fitur Gabungan:
- **Dari Azzam**: Menggunakan murni HTML5 Canvas & Vanilla JS untuk kecepatan eksekusi maksimum (tanpa loading PyScript/WASM yang lambat), pembuatan map rintangan secara prosedural (Rumput, Pohon, Sungai, Dinding), UI Interaktif (Klik posisi Player), serta visualisasi *Expanded Nodes* & Min-Heap Priority Queue yang sangat cepat.
- **Dari Salman & Zora**: Konsep **Chase Mode** di mana NPC tidak sekadar mencari jalan statis, tetapi secara aktif mengejar Player lapis demi lapis secara real-time menyesuaikan pergerakan target.

## 🚀 Algoritma yang Disertakan:
1. **Uniform Cost Search (UCS)**: $h(n) = 0$
2. **A* Search (Manhattan)**: Heuristik Jarak Manhattan (Admissible)
3. **A* Search (Euclidean)**: Heuristik Garis Lurus (Admissible)
4. **A* Search (Inadmissible)**: Membuktikan bahwa heuristik Euclidean *Squared* merusak jaminan optimalitas rute.

## 🕹️ Cara Menjalankan
1. Buka file `index.html` langsung di browser Anda. Tidak memerlukan server!
2. **Klik sembarang tempat** di peta untuk mengubah posisi Player (Target / Kuning).
3. Klik tombol **"Eksekusi Agen"** untuk melihat pencarian rute NPC (Merah).
4. Klik tombol **"🏃‍♂️ Start Chase Mode"** untuk melihat NPC memburu Player secara *real-time* seperti pada game sesungguhnya!
