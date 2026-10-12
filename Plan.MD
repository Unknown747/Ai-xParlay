# Rencana Proyek Ai-xParlay

Dokumen ini mengikuti spesifikasi di `READ.md` dan menjadi catatan utama progres proyek.

## Aturan pembaruan progres

- Perbarui checklist ini setiap kali satu poin mulai dikerjakan atau selesai.
- Tandai `[x]` hanya jika hasil poin tersebut sudah dibuat dan diperiksa; jangan menandai rencana sebagai hasil.
- Jika pekerjaan terhenti, catat kendala dan kebutuhan keputusan di bagian **Catatan dan kendala**.
- Setelah perubahan progres, perbarui ringkasan status di bawah.

## Status saat ini

- **Tahap:** Perencanaan
- **Progres implementasi:** 0%
- **Sudah dilakukan:** `READ.md` dibaca dan dirangkum menjadi rencana ini.
- **Belum dilakukan:** Belum ada kode Python, data, model, atau pengujian yang dibuat.

## Tahap 0 — Persiapan proyek

- [x] Baca `READ.md` dan susun rencana progres.
- [ ] Tentukan liga, musim, pasar, dan format keluaran untuk versi pertama.
- [ ] Siapkan struktur proyek Python tanpa mengubah stack atau memindahkan proyek.
- [ ] Siapkan dependensi dan cara menjalankan perintah proyek.
- [ ] Pastikan konfigurasi rahasia/API key tidak disimpan di Git.

**Selesai jika:** ruang lingkup versi pertama jelas, proyek bisa dijalankan, dan rahasia dikelola dengan aman.

## Tahap 1 — Pengambilan dan pemeriksaan data

- [ ] Ambil hasil pertandingan dan odds dari football-data.co.uk; target rancangan: 11 liga × 5 musim.
- [ ] Ambil data xG Understat; target rancangan: 5 liga × 5 musim.
- [ ] Simpan data historis sebagai CSV di `data/historis/` dan xG sebagai JSON di `data/understat/`.
- [ ] Tambahkan cache untuk menghindari pengambilan data berulang yang tidak perlu.
- [ ] Periksa kolom, nilai kosong, duplikat, tanggal, tim, dan kecocokan antar-sumber.
- [ ] Catat cakupan data aktual; angka target di `READ.md` bukan hasil yang sudah tercapai.

**Selesai jika:** data dapat diambil atau dimuat ulang, lolos pemeriksaan kualitas dasar, dan cakupannya terdokumentasi.

## Tahap 2 — Model statistik

- [ ] Implementasikan model Poisson untuk gol dan pasar yang didukung.
- [ ] Implementasikan model berbasis xG Understat.
- [ ] Terapkan parameter awal dari `READ.md`: `K=6`, `LAST_N=10`, `MIN_N=3`, `W_PRIOR=100`, `HOME_SHARE=0.50`, serta prior gol per liga.
- [ ] Hasilkan probabilitas untuk Over/Under 2.5, 1x2, dan BTTS sesuai ketersediaan data.
- [ ] Terapkan pengujian walk-forward: setiap prediksi hanya memakai pertandingan yang terjadi sebelumnya.
- [ ] Uji perhitungan probabilitas, termasuk rentang nilai dan konsistensi jumlah probabilitas.

**Selesai jika:** kedua model menghasilkan probabilitas yang dapat diuji tanpa kebocoran data masa depan.

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

- Belum ada kode aplikasi, dataset, maupun workflow yang dijalankan.
- Integrasi Gemini/Groq memerlukan API key dan pemeriksaan batas pemakaian ketika tahap AI dimulai.
- Klaim “akurasi sekitar 50% berarti AI tidak tahu hasil” pada `READ.md` tidak cukup sebagai bukti bahwa kebocoran data tidak ada. Validasi harus memeriksa alur data dan waktu prediksi secara langsung.
- Sumber data gratis tetap perlu diperiksa ketersediaan, format, batas akses, dan ketentuan penggunaannya saat implementasi.
