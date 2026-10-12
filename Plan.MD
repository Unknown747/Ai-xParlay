# Rencana Proyek Ai-xParlay

Dokumen ini mengikuti spesifikasi di `READ.md` dan menjadi catatan utama progres proyek.

## Aturan pembaruan progres

- Perbarui checklist ini setiap kali satu poin mulai dikerjakan atau selesai.
- Gunakan `[~]` untuk poin yang sedang dikerjakan atau belum diverifikasi, dan `[x]` hanya setelah hasilnya dibuat dan diperiksa; jangan menandai rencana sebagai hasil.
- Jika pekerjaan terhenti, catat kendala dan kebutuhan keputusan di bagian **Catatan dan kendala**.
- Setelah perubahan progres, perbarui ringkasan status di bawah.

## Keputusan cakupan (pondasi)

- **Liga (9):** E0 (Premier League), SP1 (La Liga), D1 (Bundesliga), I1 (Serie A), F1 (Ligue 1), E1 (Championship), N1 (Eredivisie), P1 (Primeira Liga), T1 (Super Lig). Semuanya punya prior gol di `READ.md`.
- **Tidak dipakai:** Belgia (`B1`) dan Skotlandia (`SC0`) ada di `READ.md` tetapi tidak ada di CSV. Liga lain di CSV (`D2`, `F2`, `G1`, `I2`, `SP2`) di luar cakupan.
- **Musim:** 5 musim penuh (2122, 2223, 2324, 2425, 2526) ditambah musim berjalan 2627 dari football-data.co.uk. Musim 2627 belum lengkap dan harus ditandai sebagai data berjalan. Jangan menambah musim lebih dari 5 musim penuh.
- **Pasar (2):** O/U 2.5 dan 1x2. BTTS dibuang (tidak ada odds BTTS di sumber; ROI tidak dapat dihitung). Keputusan ini final untuk versi proyek ini.
- **Odds untuk ROI:** Avg biasa (bukan closing), karena odds closing tidak bisa dipakai saat taruhan sungguhan.
- **Konfigurasi:** `src/config.py` (`LEAGUES`, `SEASONS`, `CURRENT_SEASON`).
- **Lingkungan:** semua pengerjaan di Termux; file ditulis dengan heredoc `cat <<'EOF'`. API key disimpan di `keys.env` (masuk `.gitignore`, jangan di-commit).

## Status saat ini

- **Tahap:** Tahap 1 selesai untuk data hasil/odds; sisa Understat (xG, 5 liga). Tahap 2 Poisson dan backtest Poisson (Tahap 5) selesai; hasilnya negatif.
- **Data:** 54/54 file (9 liga × 6 musim), 17.002 laga, 177 kolom, 2021-08-06 sampai 2026-09-20. Lima musim penuh = 16.478 laga; musim 2627 (berjalan) = 524 laga.
- **Kualitas:** 0 tanggal/skor tidak valid, 0 duplikat, 0 skor tidak lengkap, 0 FTR tidak cocok.
- **Odds:** 1x2 dan O/U 2.5 (Avg, B365, dan closing) terisi 98–100% di semua 9 liga; terendah T1 musim penuh 98%. Tidak ada liga yang dibuang.
- **Pasar (keputusan):** O/U 2.5 dan 1x2. BTTS dibuang karena sumber tidak punya odds BTTS sehingga ROI tidak bisa dihitung.
- **xG:** `HxG`/`AxG` football-data hanya terisi di 2627 (0% di musim penuh), tidak dipakai untuk backtest. xG historis dari Understat (E0, SP1, D1, I1, F1).
- **Backtest Poisson** (walk-forward, odds Avg, stake 1 unit, evaluasi dari 2022-07-01; 2122 pemanasan): 13.632 laga dievaluasi, 13.136 diprediksi (musim penuh 12.700; 2627: 436), 496 dilewati karena data kurang. `selfcheck` cocok dengan `stat_poisson.py`.
- **ROI musim penuh (±95%):** O/U semua −5,35% (±1,5); O/U filter −4,89% (±2,2); 1x2 semua −4,39% (±1,8); 1x2 filter −3,38% (±2,9). O/U negatif di keempat musim dan di 9 liga. Musim 2627 (berjalan) tidak dipakai sebagai bukti.
- **Brier model vs pasar:** O/U 0,2521 vs 0,2398; 1x2 0,6084 vs 0,5775. Odds pasar lebih akurat daripada Poisson.
- **Kesimpulan Poisson:** gagal sebagai sumber mandiri (ROI < −2%, aturan BUANG di `READ.md`); tidak dituning. Peran selanjutnya (lapisan filter ensemble atau dibuang) menunggu keputusan pengguna.
- **Belum dilakukan:** xG Understat, AI, ensemble, evaluasi akhir.

## Tahap 0 — Persiapan proyek

- [x] Baca `READ.md` dan susun rencana progres.
- [x] Tentukan jalur input awal: awalnya CSV lokal; diganti unduhan CSV statis football-data.co.uk (lihat Tahap 1).
- [x] Siapkan struktur proyek Python dan perintah inspeksi tanpa dependensi pihak ketiga.
- [x] Dokumentasikan lokasi CSV, perintah menjalankan, dan cara menjaga file data besar agar tidak masuk Git.
- [x] Tahap impor awal tidak memerlukan API key.
- [x] Tetapkan cakupan: 9 liga, 5 musim penuh + musim berjalan (lihat **Keputusan cakupan**).

**Selesai:** proyek Python dan perintah inspeksi dapat dijalankan; tahap ini memakai standard library dan tidak memerlukan rahasia.

## Tahap 1 — Pengambilan dan pemeriksaan data

- [x] Cara akses: unduh CSV statis per liga/musim (9 × 6 = 54 file) dari football-data.co.uk lewat `src/fetch_footballdata.py`; penggunaan pribadi, cache, jeda 1 detik, tanpa scraping halaman.
- [x] Jalankan `python -m src.fetch_footballdata` dan catat jumlah file/baris hasilnya. Hasil: 54/54 file, 17.002 laga, 0 gagal.
- [x] Buat pemeriksa CSV streaming untuk file besar, cakupan liga/musim, dan kualitas baris.
- [x] Pindai CSV hasil unduhan dengan `inspect_football_data.py`; catat cakupan dan kualitas aktual. Hasil: 0 nilai kosong, 0 duplikat, 0 skor/tanggal tidak valid.
- [x] Siapkan CSV ringkas dengan kolom hasil, tanggal, tim, liga, musim, dan odds yang berguna untuk model.
- [~] Pastikan Git mengabaikan `cache/`, CSV, dan `.bak`.
- [x] Tambah `src/config.py` dan filter `--leagues/--seasons/--all` di `prepare_football_data.py` (default: 9 liga, 6 kode musim).
- [~] Hapus prior `B1` dan `SC0` dari `PRIOR_GPM` di `stat_poisson.py`.
- [ ] Jalankan penyiapan CSV dengan filter; catat jumlah laga per liga dan musim, serta jumlah baris di luar cakupan.
- [x] Cek kelengkapan odds per liga (`src/check_coverage.py`): 1x2 dan O/U 2.5 terisi 98–100% di 9 liga; kolom odds BTTS tidak ada.
- [ ] Pilih atau tinjau izin sumber data untuk xG Understat sebelum mengintegrasikannya.
- [~] Batasi otomatisasi: hanya 54 file CSV yang dicache; data tidak dikirim ke AI sebelum jalur penggunaan disepakati.
- [~] Ambil data xG Understat: 5 liga (E0, SP1, D1, I1, F1) × musim 2122–2627 memakai paket `understat` (async). Probe satu liga-musim dulu; belum diverifikasi.
- [x] Tidak membuat cache unduhan: masukan awal adalah file lokal yang diproses streaming.
- [x] Periksa kolom, nilai kosong, duplikat, tanggal, tim, dan kecocokan skor/hasil pada data hasil unduhan.
- [x] Catat cakupan data aktual; angka target di `READ.md` bukan hasil yang sudah tercapai. Lihat Status saat ini.

**Selesai untuk CSV hasil/odds:** file dapat diperiksa dan dinormalisasi secara streaming sesuai cakupan; cakupan serta kualitasnya dilaporkan. Integrasi xG Understat belum dimulai.

## Tahap 2 — Model statistik

- [x] Implementasikan model Poisson untuk gol dan pasar yang didukung.
- [ ] Implementasikan model berbasis xG Understat.
- [x] Terapkan parameter awal dari `READ.md`: `K=6`, `LAST_N=10`, `MIN_N=3`, `W_PRIOR=100`, `HOME_SHARE=0.50`, serta prior gol per liga.
- [x] Hasilkan probabilitas untuk Over/Under 2.5, 1x2, dan BTTS.
- [x] Pastikan prediksi satu laga hanya memakai pertandingan bertanggal sebelum prediksi; pertandingan di tanggal yang sama dikecualikan.
- [ ] Uji rentang dan konsistensi probabilitas serta perilaku saat data tim belum mencukupi (tes belum ada di repo).

**Selesai jika:** model Poisson dan xG tersedia dan menghasilkan probabilitas tanpa memakai data masa depan.

## Tahap 3 — Integrasi AI (opsional sampai kredensial tersedia)

- [ ] Rancang satu prompt dan format keluaran terstruktur yang sama untuk semua penyedia.
- [ ] Implementasikan integrasi Gemini.
- [ ] Implementasikan integrasi Groq.
- [ ] Gunakan temperature 0 jika API mendukungnya; tanpa tanggal atau skor historis pada prompt seperti ditetapkan di `READ.md`.
- [ ] Ambil API key hanya dari `keys.env` saat tahap ini dikerjakan; jangan masukkan key ke kode atau Git.
- [ ] Tangani batas pemakaian, kegagalan API, respons tidak valid, dan biaya.

**Selesai jika:** setiap penyedia bisa dipanggil secara terpisah dan hasilnya divalidasi dengan format yang sama. Tahap ini dapat dilewati bila AI belum dipilih atau kredensial belum tersedia.

## Tahap 4 — Ensemble

- [ ] Gabungkan hasil dari minimal dua sumber yang tersedia.
- [ ] Mulai dengan filter berlapis yang direkomendasikan `READ.md`: sinyal statistik terlebih dahulu, lalu konfirmasi AI jika integrasi AI aktif.
- [ ] Catat alasan prediksi diterima atau dilewati.
- [ ] Bandingkan pendekatan filter berlapis dengan voting dan confidence-weighted sebelum memilih metode final.
- [ ] Pastikan kegagalan satu sumber tidak diam-diam dianggap sebagai prediksi yang valid.

**Selesai jika:** setiap laga menghasilkan satu pilihan atau status "skip", beserta sumber dan alasan yang dapat ditelusuri.

## Tahap 5 — Validasi dan backtest

- [x] Uji jalur data dan prediksi dari awal sampai akhir pada sampel historis. Hasil: `selfcheck` cocok (5 prediksi + 5 penolakan) dan backtest penuh berjalan.
- [ ] Periksa risiko look-ahead AI sebelum memasukkan keluaran AI ke backtest.
- [x] Jalankan backtest walk-forward pada 1.000+ laga (Poisson: 12.700 laga musim penuh 2223–2526; satu kali jalan). Hasil di Status.
- [x] Pisahkan hasil musim berjalan 2627 dari musim penuh (ditandai `*` di laporan).
- [ ] Jika AI tidak digunakan atau tidak lolos pemeriksaan, dokumentasikan alasan dan jangan mengklaim validasi AI.
- [ ] Jika AI menunjukkan risiko kebocoran hasil, jangan gunakan hasil AI historis untuk menyimpulkan performa; pertimbangkan pencatatan prospektif/live test sesuai `READ.md`.
- [x] Catat asumsi stake, odds, hasil seri/push, dan perhitungan ROI (lihat Catatan dan docstring `src/backtest.py`).

**Selesai jika:** prosedur validasi terdokumentasi, tidak memakai informasi masa depan, dan metrik dihitung dari prediksi yang dapat direproduksi.

## Tahap 6 — Evaluasi sumber dan pasar

- [~] Evaluasi ROI dan akurasi secara terpisah untuk Poisson, xG, Gemini, Groq, dan ensemble. Poisson selesai (lihat Status); lainnya belum ada.
- [~] Bandingkan O/U 2.5 dan 1x2 (BTTS dibuang: tidak ada odds). Poisson: keduanya negatif; belum ada pembeda antar pasar.
- [~] Periksa konsistensi hasil per minggu/periode. Per musim dan per liga selesai untuk Poisson; per minggu belum.
- [ ] Terapkan kriteria keputusan dari `READ.md` sebagai panduan evaluasi, bukan jaminan keuntungan.
- [~] Dokumentasikan sumber yang dipertahankan, dinonaktifkan, atau perlu diuji lagi. Poisson mandiri: gagal ambang READ.md; peran akhir menunggu keputusan pengguna.

**Selesai jika:** laporan menunjukkan metrik, cakupan sampel, dan alasan untuk setiap keputusan.

## Tahap 7 — Pencatatan prospektif dan keputusan penggunaan

- [ ] Jika backtest AI tidak dapat dipercaya, catat prediksi sebelum pertandingan selama periode uji yang ditentukan.
- [ ] Target rancangan `READ.md`: 30 hari dan sedikitnya 100 laga untuk evaluasi prospektif.
- [ ] Bandingkan hasil aktual dengan prediksi dan odds yang tersedia pada saat prediksi.
- [ ] Putuskan apakah proyek dilanjutkan, pasar/liga diganti, atau pengembangan dihentikan.
- [ ] Jangan mengaktifkan taruhan otomatis; hasil sistem adalah prediksi dan evaluasi, bukan jaminan ROI.

**Selesai jika:** keputusan penggunaan didukung catatan uji dan batasan sistem dipahami.

## Catatan dan kendala

- Belum ada xG, ensemble, AI, atau backtest. File dataset sumber/hasil tidak disimpan di Git; alat berupa perintah Python satu kali dari terminal (`python -m src.<modul>`).
- `stat_poisson.py` saat ini membaca seluruh CSV untuk setiap prediksi; backtest membutuhkan jalur satu kali jalan.
- Liga tanpa prior di `PRIOR_GPM` memakai rata-rata liga yang diamati sebelum laga; ke-9 liga cakupan semuanya punya prior.
- Halaman resmi football-data.co.uk menyatakan penggunaan ditujukan bagi individu pribadi dan bukan untuk penggunaan komersial atau produk data-training yang memakai bot/scraper/AI. Pengambilan otomatis dan pengiriman data ke AI ditahan sampai jalur penggunaan disepakati.
- Integrasi Gemini/Groq memerlukan API key dan pemeriksaan batas pemakaian ketika tahap AI dimulai.
- Klaim "akurasi sekitar 50% berarti AI tidak tahu hasil" pada `READ.md` tidak cukup sebagai bukti bahwa kebocoran data tidak ada. Validasi harus memeriksa alur data dan waktu prediksi secara langsung.
- Sumber data gratis tetap perlu diperiksa ketersediaan, format, batas akses, dan ketentuan penggunaannya saat implementasi.
- football-data.co.uk menyediakan satu CSV per liga/musim tanpa kolom `Season`; `src/fetch_footballdata.py` menambahkan `Season` dan `Div` saat menggabungkan ke `data/historis/all_football_data.csv`. Hanya 54 file statis, dicache di `cache/footballdata/`; musim berjalan 2627 diunduh ulang setiap kali dijalankan.
- Sumber football-data.co.uk tidak memiliki kolom odds BTTS di antara 177 kolom; ROI BTTS tidak dapat dihitung dengan odds nyata dari sumber ini. Keputusan: BTTS dibuang dari evaluasi ROI.
- Understat hanya mencakup E0, SP1, D1, I1, F1; E1, N1, P1, T1 tidak punya model xG.
- Hasil `check_coverage.py`: odds 1x2/O/U terisi 98–100% di semua liga musim penuh dan 100% di 2627; `HxG`/`AxG` hanya terisi di 2627, jadi tidak dipakai untuk backtest.
- Asumsi backtest: stake tetap 1 unit; profit = odds-1 jika menang, -1 jika kalah; tanpa push; odds Avg football-data dianggap tersedia; tanpa komisi/batas taruhan; laga tanpa odds dilewati. Mode 'semua' = taruh di pilihan model tiap laga; mode 'filter' = O/U |p-0.5|>0.1 (READ.md) dan 1x2 p_pilihan>0.6 (analog buatan, bukan dari READ.md). Ambang tetap dan tidak dituning. Musim 2122 hanya pemanasan (evaluasi dari 2022-07-01); musim 2627 dilaporkan terpisah.
- `src/backtest.py` punya `--selfcheck` yang mencocokkan sampel prediksi dengan `stat_poisson.predict_match`; jika gagal, hasil tidak boleh dipakai.
- Catatan statistik (perkiraan): 100 laga live dengan odds sekitar 1,8 memberi ketidakpastian ROI kira-kira ±19%, sehingga tidak cukup membuktikan edge +2%. Keputusan Tahap 7 perlu memperhitungkan ini.
- Pada backtest Poisson, laga yang dilewati (496) adalah laga dengan riwayat liga/tim di bawah MIN_N; kasus ini ditolak sama persis oleh `stat_poisson.py` (diverifikasi `selfcheck`).
- FBref tidak lagi menyediakan xG sejak Januari 2026 (Opta memutus kontrak data lanjutan), sehingga `fbrefdata` dan `stat_xg_fbref.py` di READ.md tidak dipakai.
- Paket `understat` (async) berbeda dari `understatapi` yang disebut READ.md; kecocokannya dengan situs saat ini harus diverifikasi lewat probe.
