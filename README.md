# Tubes Kecerdasan Buatan - Kelompok 13 🚀

Repositori ini berisi seluruh implementasi algoritma pencarian (Tahap 1 & Tahap 2) oleh Kelompok 13 untuk mata kuliah Kecerdasan Buatan.

**Anggota Kelompok:**
1. Azzam Muhammad Naufal (2007763)
2. Salman Ghiffari (2509646)
3. Zora Riyadhul Jinan (2509722)

---

## 🧭 Struktur Proyek (Monorepo)

Semua karya anggota digabungkan dalam satu portal agar mudah ditinjau. Silakan buka **`index.html`** di browser Anda untuk melihat UI Portal Utama.

```text
codebase/
├── index.html                  # PORTAL UTAMA (Buka ini di Browser)
├── README.md
├── Tubes1_InformedSearch/
│   ├── Azzam/                  # A* Interactive Canvas Map
│   └── Salman_Zora/            # PyScript Grid Chase
└── Tubes2_AdversarialSearch/
    ├── Azzam/                  # INTERCEPT Game (Minimax vs Alpha-Beta)
    ├── Salman/                 # Samurai Duel (Flask Backend)
    └── Zora/                   # Grid + Battle (PyScript Expectimax)
```

---

## 🎮 Cara Menjalankan

### 1. Buka Portal Utama (Direkomendasikan)
Cukup klik ganda file `index.html` di root folder ini menggunakan browser (Chrome/Edge/Safari). Portal ini memiliki tautan interaktif ke setiap proyek.

### 2. Menjalankan Proyek Salman (Tahap 2 - Flask)
Karena proyek Tahap 2 milik Salman menggunakan *backend* Flask (Python), aplikasi ini **tidak bisa dibuka langsung lewat browser**. Anda harus menjalankan server lokal terlebih dahulu:

1. Buka Terminal / Command Prompt.
2. Navigasikan ke direktori proyek Salman:
   ```bash
   cd Tubes2_AdversarialSearch/Salman
   ```
3. Install dependencies (Flask):
   ```bash
   pip install -r requirements.txt
   ```
4. Jalankan server:
   ```bash
   python app.py
   ```
5. Buka `http://127.0.0.1:5000` di browser.

### 3. Proyek Zora (PyScript)
Aplikasi buatan Zora dan Salman (Tahap 1) menggunakan PyScript. Saat pertama kali dibuka di browser, *harap tunggu sekitar 5-10 detik* karena browser harus mengunduh *runtime* Python berbasis WebAssembly (Pyodide).

---
*Dibuat untuk memenuhi Tugas Besar Kecerdasan Buatan (UPI).*
