# Rencana Proyek Ai-xParlay

Dokumen ini mengikuti spesifikasi di `READ.md` dan menjadi catatan utama progres proyek.

## Aturan pembaruan progres

- Perbarui checklist ini setiap kali satu poin mulai dikerjakan atau selesai.
- Gunakan `[~]` untuk poin yang sedang dikerjakan dan `[x]` hanya setelah hasilnya dibuat dan diperiksa; jangan menandai rencana sebagai hasil.
- Jika pekerjaan terhenti, catat kendala dan kebutuhan keputusan di bagian **Catatan dan kendala**.
- Setelah perubahan progres, perbarui ringkasan status di bawah.

## Status saat ini

- **Tahap:** Tahap 2 — model Poisson pertama selesai; model xG dan backtest belum dimulai.
- **Progres implementasi:** Fondasi, penyiapan CSV, dan prediksi Poisson untuk satu laga selesai serta diverifikasi.
- **Sudah dilakukan:** CSV penuh dari tautan pengguna dipindai dan dinormalisasi di direktori sementara; 13 tes otomatis serta satu prediksi uji dari seluruh dataset lulus.
- **Belum dilakukan:** File sumber/hasil belum disimpan ke workspace; model xG, AI, ensemble, dan evaluasi backtest belum dibuat.
- **Cakupan CSV:** 107.408 baris, 218 kolom, 14 kode liga, 22 musim (0506–2627); musim 2627 masih berjalan.
- **Kualitas awal:** 0 tanggal/skor tidak valid, 0 fixture duplikat, 0 hasil yang tidak cocok dengan skor; dari 106 baris tanpa skor, 103 baris kosong tanpa tanggal/tim dan 3 fixture valid.
- **Pasar awal:** O/U 2.5, 1x2, BTTS, mengikuti `READ.md`.
- **Ukuran file sumber:** 55.361.364 byte (sekitar 55,4 MB); pemindaian memakai file sementara yang sudah dihapus setelahnya.
- **CSV ringkas:** 107.305 baris × 29 kolom; 11.444.234 byte (sekitar 11,4 MB). Tidak disimpan ke workspace.

## Tahap 0 — Persiapan proyek

- [x] Baca `READ.md` dan susun rencana progres.
- [x] Tentukan jalur input awal: impor CSV lokal dari pengguna, bukan scraper football-data.co.uk.
- [x] Tetapkan cakupan versi pertama: pertahankan semua liga/musim di CSV; pasar mengikuti `READ.md`.
- [x] Siapkan struktur proyek Python dan perintah inspeksi tanpa dependensi pihak ketiga.
- [x] Dokumentasikan lokasi CSV, perintah menjalankan, dan cara menjaga file data besar agar tidak masuk Git.
- [x] Tahap impor awal tidak memerlukan API key.

**Selesai:** proyek Python dan perintah inspeksi dapat dijalankan; tahap ini memakai standard library dan tidak memerlukan rahasia.

## Tahap 1 — Pengambilan dan pemeriksaan data

- [x] Pilih cara akses awal: CSV lokal yang diberikan pengguna; tidak membuat scraper football-data.co.uk.
- [x] Buat pemeriksa CSV streaming untuk file besar, cakupan liga/musim, dan kualitas baris.
- [x] Pindai penuh CSV yang diberikan melalui file sementara tanpa menyimpan salinan 55 MB di proyek atau Git.
- [x] Siapkan CSV ringkas dengan kolom hasil, tanggal, tim, liga, musim, dan odds yang berguna untuk tahap model.
- [x] Pastikan Git mengabaikan CSV sumber dan hasil ringkas.
- [ ] Pilih atau tinjau izin sumber data untuk xG Understat sebelum mengintegrasikannya.
- [x] Tahan otomatisasi pengambilan data eksternal sampai ketentuan penggunaan mengizinkannya.
- [ ] Ambil data xG Understat; target rancangan: 5 liga × 5 musim.
- [x] Gunakan file CSV lokal yang sama sebagai sumber; jangan menggandakan file 55 MB di Git.
- [x] Tidak membuat cache unduhan: masukan awal adalah file lokal yang diproses streaming.
- [x] Periksa kolom, nilai kosong, duplikat, tanggal, tim, dan kecocokan skor/hasil.
- [x] Catat cakupan data aktual; angka target di `READ.md` bukan hasil yang sudah tercapai.

**Selesai untuk CSV hasil/odds:** file dapat diperiksa dan dinormalisasi secara streaming; cakupan serta kualitasnya dilaporkan. Integrasi xG Understat belum dimulai.

## Tahap 2 — Model statistik

- [x] Implementasikan model Poisson untuk gol dan pasar yang didukung.
- [ ] Implementasikan model berbasis xG Understat.
- [x] Terapkan parameter awal dari `READ.md`: `K=6`, `LAST_N=10`, `MIN_N=3`, `W_PRIOR=100`, `HOME_SHARE=0.50`, serta prior gol per liga.
- [x] Hasilkan probabilitas untuk Over/Under 2.5, 1x2, dan BTTS.
- [x] Pastikan prediksi satu laga hanya memakai pertandingan bertanggal sebelum prediksi; pertandingan di tanggal yang sama dikecualikan.
- [x] Uji rentang dan konsistensi probabilitas serta perilaku saat data tim belum mencukupi.

**Status tahap:** model Poisson awal selesai; model xG dan backtest masih tertunda.

**Selesai jika:** model Poisson dan xG tersedia dan menghasilkan probabilitas tanpa memakai data masa depan.

## Tahap 3 — Integrasi AI (opsional sampai kredensial tersedia)

- [ ] Rancang satu prompt dan format keluaran terstruktur yang sama untuk semua penyedia.
- [ ] Implementasikan integrasi Gemini.
- [ ] Implementasikan integrasi Groq.
- [ ] Gunakan temperature 0 jika API mendukungnya; tanpa tanggal atau skor historis pada prompt seperti ditetapkan di `READ.md`.
- [ ] Ambil API key hanya dari Replit Secrets saat tahap ini dikerjakan; jangan masukkan key ke kode atau Git.
- [ ] Tangani batas pemakaian, kegagalan API, respons tidak valid, dan biaya.

**Selesai jika:** setiap penyedia bisa dipanggil secara terpisah dan hasilnya divalidasi dengan format yang sama. Tahap ini dapat dilewati bila AI belum dipilih atau kredensial belum tersedia.

## Tahap 4 — Ensemble

- [ ] Gabungkan hasil dari minimal dua sumber yang tersedia.
- [ ] Mulai dengan filter berlapis yang direkomendasikan `READ.md`: sinyal statistik terlebih dahulu, lalu konfirmasi AI jika integrasi AI aktif.
- [ ] Catat alasan prediksi diterima atau dilewati.
- [ ] Bandingkan pendekatan filter berlapis dengan voting dan confidence-weighted sebelum memilih metode final.
- [ ] Pastikan kegagalan satu sumber tidak diam-diam dianggap sebagai prediksi yang valid.

**Selesai jika:** setiap laga menghasilkan satu pilihan atau status “skip”, beserta sumber dan alasan yang dapat ditelusuri.

## Tahap 5 — Validasi dan backtest

- [ ] Uji jalur data dan prediksi dari awal sampai akhir pada sampel historis.
- [ ] Periksa risiko look-ahead AI sebelum memasukkan keluaran AI ke backtest.
- [ ] Jalankan backtest walk-forward pada 1.000+ laga bila cakupan data memadai.
- [ ] Jika AI tidak digunakan atau tidak lolos pemeriksaan, dokumentasikan alasan dan jangan mengklaim validasi AI.
- [ ] Jika AI menunjukkan risiko kebocoran hasil, jangan gunakan hasil AI historis untuk menyimpulkan performa; pertimbangkan pencatatan prospektif/live test sesuai `READ.md`.
- [ ] Catat asumsi stake, odds, hasil seri/push, dan perhitungan ROI agar evaluasi dapat direproduksi.

**Selesai jika:** prosedur validasi terdokumentasi, tidak memakai informasi masa depan, dan metrik dihitung dari prediksi yang dapat direproduksi.

## Tahap 6 — Evaluasi sumber dan pasar

- [ ] Evaluasi ROI dan akurasi secara terpisah untuk Poisson, xG, Gemini, Groq, dan ensemble yang benar-benar tersedia.
- [ ] Bandingkan O/U 2.5, 1x2, dan BTTS bila data odds mendukung.
- [ ] Periksa konsistensi hasil per minggu/periode, bukan hanya angka gabungan.
- [ ] Terapkan kriteria keputusan dari `READ.md` sebagai panduan evaluasi, bukan jaminan keuntungan.
- [ ] Dokumentasikan sumber yang dipertahankan, dinonaktifkan, atau perlu diuji lagi.

**Selesai jika:** laporan menunjukkan metrik, cakupan sampel, dan alasan untuk setiap keputusan.

## Tahap 7 — Pencatatan prospektif dan keputusan penggunaan

- [ ] Jika backtest AI tidak dapat dipercaya, catat prediksi sebelum pertandingan selama periode uji yang ditentukan.
- [ ] Target rancangan `READ.md`: 30 hari dan sedikitnya 100 laga untuk evaluasi prospektif.
- [ ] Bandingkan hasil aktual dengan prediksi dan odds yang tersedia pada saat prediksi.
- [ ] Putuskan apakah proyek dilanjutkan, pasar/liga diganti, atau pengembangan dihentikan.
- [ ] Jangan mengaktifkan taruhan otomatis; hasil sistem adalah prediksi dan evaluasi, bukan jaminan ROI.

**Selesai jika:** keputusan penggunaan didukung catatan uji dan batasan sistem dipahami.

## Catatan dan kendala

- Belum ada xG, ensemble, AI, atau backtest. File dataset sumber/hasil tidak disimpan permanen di workspace; alat yang dibuat berupa perintah Python satu kali dari terminal, bukan workflow server.
- File yang diberikan memiliki header seperti `Date`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `FTR`, `League`, `LeagueCode`, dan `Season`, beserta banyak kolom odds/statistik serta kolom tambahan. Pemeriksa perlu streaming dan hanya mewajibkan kolom yang dibutuhkan.
- File penuh berisi 14 kode liga (`D1`, `D2`, `E0`, `E1`, `F1`, `F2`, `G1`, `I1`, `I2`, `N1`, `P1`, `SP1`, `SP2`, `T1`) dan musim berjalan `2627`. Jangan mengasumsikan cakupannya persis 11 liga × 5 musim.
- Dari 106 baris mentah tanpa skor penuh, 103 adalah baris kosong tanpa tanggal/tim dan dilewati; 3 fixture yang dapat dikenali dipertahankan tanpa hasil.
- CSV ringkas berhasil diuji penuh: 55.361.364 byte menjadi 11.444.234 byte, tanpa hasil yang tidak cocok atau fixture duplikat. File sementara dihapus setelah verifikasi.
- Model Poisson menghasilkan probabilitas pada data uji menggunakan 8.030 hasil liga sebelum tanggal prediksi dan 10 laga venue terakhir per tim. Ini uji fungsi, bukan bukti akurasi atau ROI.
- Musim `2627` belum selesai; jangan gabungkan hasilnya dengan musim penuh tanpa menandainya sebagai data berjalan.
- Halaman resmi football-data.co.uk menyatakan penggunaan ditujukan bagi individu pribadi dan bukan untuk penggunaan komersial atau produk data-training yang memakai bot/scraper/AI. Pengambilan otomatis dan pengiriman data ke AI ditahan sampai jalur penggunaan disepakati.
- Integrasi Gemini/Groq memerlukan API key dan pemeriksaan batas pemakaian ketika tahap AI dimulai.
- Klaim “akurasi sekitar 50% berarti AI tidak tahu hasil” pada `READ.md` tidak cukup sebagai bukti bahwa kebocoran data tidak ada. Validasi harus memeriksa alur data dan waktu prediksi secara langsung.
- Sumber data gratis tetap perlu diperiksa ketersediaan, format, batas akses, dan ketentuan penggunaannya saat implementasi.
