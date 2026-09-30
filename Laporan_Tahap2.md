# Laporan Tugas Besar Tahap 2: Adversarial Search
**Mata Kuliah:** Kecerdasan Buatan  
**Anggota Kelompok:** Kelompok 13  
*(Azzam Muhammad Naufal, Salman Ghiffari, Zora Riyadhul Jinan)*

---

## 1. Definisi Konseptual (Turn-Based Battle)

Adversarial Search diterapkan dalam fitur **Turn-Based Battle**. Mode ini terpicu ketika jarak Euclidean antara Player dan NPC di *grid* mencapai $\le 2$.

### A. State
State pertempuran direpresentasikan dengan *tuple* `(php, nhp, ppot, npot, psh, nsh, turn)`:
- `php`, `nhp`: *Health Points* Player dan NPC (Maksimal 100).
- `ppot`, `npot`: Sisa jumlah Potion yang dimiliki Player dan NPC (Mulai dari 2).
- `psh`, `nsh`: Status perisai (*Shield*) aktif atau tidak (Boolean).
- `turn`: Penanda giliran `"P"` (Player/MIN) atau `"N"` (NPC/MAX).

### B. Action
Setiap agen maksimal memiliki branching factor $\le 3$:
1. `attack`: Mengurangi HP lawan sebesar `20` (atau `10` jika lawan sedang memiliki *shield*). Menonaktifkan *shield* sendiri.
2. `defend`: Mengaktifkan *shield* (mengurangi *damage* serangan berikutnya sebesar 50%).
3. `potion`: Mengembalikan HP sebesar `30`. Hanya legal jika sisa `potion > 0` dan `HP < 100`.

### C. Terminal Test
Permainan (atau simulasi tree) berakhir jika salah satu karakter kehabisan HP.
`Terminal_Test(s)` bernilai **True** jika `s.php <= 0` atau `s.nhp <= 0`.

### D. Utility
Fungsi objektif dievaluasi dari sudut pandang **NPC (Node MAX)**. Menggunakan *Depth Bonus* agar NPC memilih jalur kemenangan tercepat, dan menunda kekalahan selama mungkin:
- Jika `php <= 0` (NPC Menang) $\rightarrow Utility = 1000 + d$
- Jika `nhp <= 0` (Player Menang) $\rightarrow Utility = -1000 - d$

*(di mana $d$ adalah sisa kedalaman pencarian saat mencapai terminal state)*

### E. Evaluation Function
Untuk simpul yang dipotong pada batas *depth limit* (bukan terminal), state diestimasi menggunakan beberapa variasi fungsi evaluasi heuristik:
1. **Balanced:** `(nhp - php) + 12*(npot - ppot) + 8*(nsh - psh)`  
   *Menyeimbangkan serangan, pertahanan, dan alokasi sumber daya.*
2. **Aggressive:** `0.5 * nhp - 2.0 * php`  
   *Fokus besar pada mengurangi HP lawan, meremehkan pertahanan diri.*
3. **Defensive:** `2.0 * nhp - 0.5 * php + 12 * npot + 8 * nsh`  
   *Fokus bertahan hidup, menghemat potion dan terus memakai shield.*

---

## 2. Eksperimen dan Hasil

Serangkaian eksperimen otomatis (`experiments.py`) dijalankan ribuan iterasi secara *headless* (di luar browser). Berikut laporannya:

### Eksperimen 1: Minimax vs Alpha-Beta Pruning (Efisiensi Node)
Dari pengujian kedalaman pohon 1 hingga 10:
*   **Depth 4:** Minimax rata-rata mengekspansi **105 node**. Alpha-Beta memangkasnya menjadi **56 node** (Hemat ~45%).
*   **Depth 8:** Minimax mengekspansi **~8.200 node**. Alpha-Beta hanya mengekspansi **~1.100 node** (Hemat ~85%). Waktu eksekusi turun drastis dari ~35ms menjadi ~4ms.
*   **Early Stop:** Menambahkan limit budget node (misal max 100 node) dengan Alpha-Beta menjaga UI bebas dari lag walau disetel ke Depth 10. Keputusan heuristik diambil dari daun yang dipotong di tengah jalan.

### Eksperimen 2 & 5: Fungsi Evaluasi & Tingkah Laku (Behavior)
NPC diadu melawan pemain simulasi (*Attacker* statis, *Random*, dan *Minimax-d4*).
*   **NPC Aggressive:** Sering menukar *damage*. Menang cepat melawan *Random*, namun *Win Rate* turun menjadi 45% saat melawan *Minimax-d4* (karena terjebak kehabisan HP tanpa melakukan *heal*).
*   **NPC Defensive:** Persentase aksi *defend* dan *potion* naik hingga 60%. Pertandingan berlangsung lama (rata-rata ronde naik 3x lipat), *Win Rate* melawan musuh berat sangat stabil (88%).
*   **NPC Balanced:** Memberikan tingkat kemenangan paling optimal (94%) lintas berbagai lawan, bereaksi dengan *potion* tepat sebelum mati, dan berani menyerang saat musuh tidak ber-shield.

### Eksperimen 3: Perbandingan Urutan Aksi (Move Ordering)
Diuji menggunakan *Alpha-Beta* pada Depth 8:
*   **Default** (`attack`, `defend`, `potion`): Menggunakan rata-rata 1100 Node.
*   **Heuristic Sort:** Mengurutkan calon langkah berdasarkan estimasi evaluasi 1-lapis ke depan. Ekspansi node turun menjadi **~420 Node**.
*   **Kesimpulan:** Urutan iterasi cabang sangat vital bagi algoritma Alpha-Beta. Anak dengan nilai terbaik yang dievaluasi lebih dulu akan mempercepat proses pemangkasan (Cutoff) untuk Alpha maupun Beta.

### Eksperimen 4: Perbandingan Kedalaman (Depth Limit)
*   **Depth 1-2:** NPC "rabun dekat". Sering membuang Potion di awal turn tanpa memikirkan konsekuensi jangka panjang.
*   **Depth 4:** Batas optimal *real-time*. NPC mulai tahu kapan harus menyimpan Potion untuk late-game.
*   **Depth 6+:** Mulai melihat kemungkinan 3 giliran ke depan (menghindari kekalahan paksa). *Win rate* meningkat dari 82% (d2) menjadi 95% (d6).

### Eksperimen 6: Expectimax vs Alpha-Beta (Probabilitas)
Saat disimulasikan bahwa *Player* mengambil langkah acak (Random Uniform, prob=33% tiap aksi):
*   **Alpha-Beta** berasumsi *Player* selalu melakukan balasan paling optimal/mematikan. Ini membuat Alpha-Beta bermain terlalu "Pengecut" (*pessimistic*) saat HP kritis.
*   **Expectimax** berasumsi lawan bergerak secara probabilitas (Chance Node = $\sum P(a_i) \times Value(a_i)$). Expectimax bermain lebih berani dan menghasilkan *Win Rate* 3-4% lebih tinggi melawan pemain *Random* atau *Attacker* membabi buta, karena ia memanfaatkan kemungkinan bahwa lawan akan "melakukan blunder".
