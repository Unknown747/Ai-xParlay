# Ai-xParlay


---

TEMPLATE PROJECT — PREDIKSI HYBRID

Form untuk membangun sistem prediksi sepak bola dengan multi-sumber: statistik + xG + AI.
Fokus: ensemble → satu suara. Bisa buang sumber jelek.

---

1. TUJUAN

Bangun sistem prediksi yang:

· Gabung statistik (Poisson, xG) + AI (Gemini, Groq)
· Uji beberapa pasar (O/U 2.5, 1x2, BTTS) — pilih yang terbaik
· Hasil: satu suara prediksi per laga
· Evaluasi: ROI vs odds nyata

---

2. STRUKTUR FOLDER

```
proyek-baru/
├── README.md
├── ROADMAP.md
├── keys.env              ← API keys (jangan commit)
├── data/
│   ├── historis/         ← football-data.co.uk (CSV)
│   └── understat/        ← xG (JSON)
├── cache/                ← cache fetch
├── src/
│   ├── fetch_footballdata.py
│   ├── fetch_understat.py
│   ├── stat_poisson.py
│   ├── stat_xg.py
│   ├── ai_gemini.py
│   ├── ai_groq.py
│   └── ensemble.py
├── backtest.py
├── live.py
├── evaluate.py
└── harian.sh
```

---

3. FASE

Fase 1: Data (1-2 hari)

· Fetch football-data.co.uk: 11 liga × 5 musim
· Fetch Understat: 5 liga × 5 musim
· Output: ~15.000 laga (odds + hasil), ~9.000 laga (xG)

Fase 2: Model Statistik (1 hari)

· stat_poisson.py: input 10 laga terakhir, output p_over/p_home/p_draw/p_away/p_btts
· stat_xg.py: input xG 10 laga terakhir, output sama
· Walk-forward

Fase 3: AI (1 hari)

· ai_gemini.py: prompt → pick + confidence
· ai_groq.py: sama
· Temperature = 0, prompt sama untuk semua AI

Fase 4: Ensemble (1 hari)

· Gabung semua sumber
· Filter berlapis: statistik filter → AI konfirmasi → taruhan

Fase 5: Backtest / Live (30 hari)

· Uji look-ahead dulu (20 laga historis)
· Kalau AI tidak tahu hasil → backtest 1000+ laga
· Kalau AI tahu hasil → live test 30 hari, 100 laga

Fase 6: Keputusan

· ROI > +2% konsisten → lanjut produksi
· ROI < 0 → berhenti, ganti pasar

---

4. SUMBER DATA

Sumber Isi Biaya
football-data.co.uk Hasil + odds (O/U, 1x2) Gratis
Understat (understatapi) xG 5 liga Gratis
FBref (fbrefdata) xG 11 liga Gratis
Gemini AI Free tier
Groq AI Free tier

---

5. PARAMETER STATISTIK

```
K          = 6        # bobot prior
LAST_N     = 10       # 10 laga terakhir
MIN_N      = 3        # min laga per tim
W_PRIOR    = 100      # bobot prior liga
HOME_SHARE = 0.50     # porsi gol kandang

PRIOR_GPM per liga:
  epl: 2.88, laliga: 2.96, bundesliga: 3.86,
  seriea: 2.85, ligue1: 2.88, championship: 2.83,
  eredivisie: 3.74, primeira: 2.72, belgia: 2.97,
  superlig: 2.92, skotlandia: 2.61
```

---

6. PROMPT AI

```
Prediksi [pasar] untuk [Home] vs [Away] di [Liga].

Konteks:
- [Home]: posisi [X], 5 laga terakhir [hasil]
- [Away]: posisi [Y], 5 laga terakhir [hasil]

Jawab HANYA:
PILIHAN: [Opsi1] / [Opsi2] / Tidak tahu
CONFIDENCE: 0-100
ALASAN: (max 20 kata)
```

Aturan:

· ✅ Temperature = 0
· ✅ Prompt sama untuk semua AI
· ❌ Jangan kasih tanggal
· ❌ Jangan kasih skor historis

---

7. ENSEMBLE

Opsi A: Voting

```
4 sumber: Poisson, xG, Gemini, Groq
3+ setuju → taruhan
2-2 → skip
```

Opsi B: Confidence-weighted

```
Tiap sumber kasih 0-1:
  > 0.65 → Over
  < 0.35 → Under
  0.35-0.65 → skip
```

Opsi C: Filter berlapis

```
1. Statistik: |p - 0.5| > 0.1
2. AI: harus setuju
3. Kalau setuju → taruhan
```

Rekomendasi: C.

---

8. VALIDASI

Uji look-ahead (wajib)

```
1. Ambil 20 laga historis
2. Tanya AI (tanpa tanggal)
3. Bandingkan dengan hasil

AI benar > 70% → TAHU HASIL → backtest tidak valid
AI benar ~50%  → tidak tahu → backtest valid
```

Kalau AI tidak tahu hasil

· Backtest 1000+ laga
· Hitung ROI per sumber
· Ensemble

Kalau AI tahu hasil

· Live test 30 hari
· Kumpulkan 100+ laga
· Hitung ROI

---

9. CHECKLIST — BISA BUANG KALAU JELEK

Sumber

```
[ ] stat_poisson.py     — Poisson gol
[ ] stat_xg.py          — Poisson xG Understat
[ ] stat_xg_fbref.py    — Poisson xG FBref
[ ] ai_gemini.py        — Gemini
[ ] ai_groq.py          — Groq
    ↳ BUANG kalau ROI < -2% di 100 laga
    ↳ BUANG kalau look-ahead tinggi
    ↳ BUANG kalau biaya tinggi
```

Ensemble

```
[ ] Voting sederhana
[ ] Confidence-weighted
[ ] Filter berlapis
    ↳ Pilih SATU
    ↳ Kalau voting jelek → confidence
    ↳ Kalau confidence jelek → filter
```

Pasar

```
[ ] O/U 2.5
[ ] 1x2
[ ] BTTS
    ↳ Uji 3, pilih yang ROI positif
    ↳ BUANG yang ROI negatif
```

File (hapus setelah selesai)

```
[ ] tune_*.py
[ ] kalibrasi_*.py
[ ] *_backup.py
[ ] *.bak, *.bak2, *.bak3
[ ] *_lama.csv
```

---

10. EVALUASI (setelah 100 laga)

```
1. ROI per sumber:
   Poisson:    ....%
   xG:         ....%
   Gemini:     ....%
   Groq:       ....%
   Ensemble:   ....%

2. Sumber mana paling akurat?
3. Ensemble > masing-masing sumber?
4. Konsisten per minggu?

5. Keputusan:
   ROI ensemble > +2% → lanjut
   ROI ensemble < 0   → berhenti
```

---

11. KEPUTUSAN

ROI positif konsisten

· Lanjut produksi
· Skala lebih banyak laga
· Monitoring mingguan

ROI negatif

· BERHENTI
· Jangan tuning
· Jangan ganti prompt
· Jangan tambah sumber
· Pilihan:
  · Ganti pasar
  · Ganti liga
  · Berhenti total

---

12. ATURAN EMAS

```
1. Uji look-ahead dulu sebelum pakai AI
2. Ensemble minimal 2 sumber
3. Temperature AI = 0
4. Prompt sama untuk semua AI
5. Jangan kasih tanggal ke AI
6. Backtest > 1000 laga sebelum keputusan
7. Jangan tuning kalau gagal
8. Jangan cari kombinasi ajaib
9. Backup sebelum regenerate
10. Hapus backup setelah selesai
11. Jangan taruhan sebelum 100 laga live
12. Pasar top Eropa efisien
```

---

13. LANGKAH PERTAMA

```
1. Buat folder:
   mkdir proyek-baru && cd proyek-baru
   mkdir -p data/historis data/understat cache src

2. Fetch data:
   - football-data.co.uk (11 liga × 5 musim)
   - Understat (5 liga × 5 musim)

3. Tulis stat_poisson.py
4. Tulis stat_xg.py
5. Tulis ai_gemini.py
6. Tulis ai_groq.py
7. Tulis ensemble.py
8. Uji look-ahead
9. Backtest / live test
10. Evaluasi, buang sumber jelek
```

---

14. SATU PARAGRAF PENUTUP

Hybrid mungkin punya edge. Statistik gagal sendiri, AI mungkin punya look-ahead, tapi ensemble bisa lebih baik. Kunci: uji look-ahead dulu, live test 100 laga, buang sumber jelek, ensemble ulang. Kalau tetap negatif, berhenti. Jangan tuning. Jangan cari kombinasi ajaib. Fokus: uji, buang, ensemble, ulangi.

---
