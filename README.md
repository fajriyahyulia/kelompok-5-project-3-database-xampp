# Sistem Pengelolaan Peminjaman Peralatan Laboratorium (Text File + MariaDB)

Proyek 2 Praktikum Pemrograman Dasar. Lanjutan Proyek 1: logika peminjaman yang sama, tetapi seluruh data disimpan permanen di text file (.txt) sehingga tidak hilang saat program ditutup. Selama program berjalan, data dikelola dalam List dan Dictionary.

## Versi Database (MariaDB)

Kode Proyek 2 tetap dipakai utuh. Yang ditambahkan hanyalah lapisan penyimpanan ke MariaDB lewat PyMySQL, mengikuti pola Modul 10 (class `Database`, Repository, transaksi `commit` dan `rollback`, query berparameter `%s`).

- **Data utama ada di MariaDB** (database `peminjaman_lab`, enam tabel, dengan Primary Key, Foreign Key `ON DELETE RESTRICT`, `UNIQUE`, dan `CHECK`). Skema ada di [sql/skema.sql](sql/skema.sql) dan dibuat otomatis saat program pertama kali jalan.
- **Text file tetap ada.** Setelah setiap penyimpanan ke database berhasil, isi `data/*.txt` ditulis ulang sebagai cermin. Karena itu backup dan pemulihan, ekspor laporan, dan `log.txt` bekerja seperti sebelumnya.
- **Migrasi otomatis.** Bila database masih kosong, program mengisinya dari `data/*.txt` (data contoh ikut masuk).
- **Aman bila database mati.** Jika MariaDB tidak menyala atau PyMySQL belum terpasang, program memberi tahu alasannya lalu berjalan dalam mode text file seperti Proyek 2 asli. Mode ini juga bisa dipaksa dengan `PEMINJAMAN_MODE=txt`.
- **Aturan 7 tetap berlaku.** Satu operasi disimpan dalam satu transaksi database. Bila gagal, database di-rollback dan perubahan di memori dibatalkan.

### Cara menjalankan

1. Nyalakan **MySQL** di XAMPP Control Panel (Apache tidak wajib).
2. `pip install -r requirements.txt` (hanya `pymysql`).
3. `python main.py`. Baris pertama menu menunjukkan `Penyimpanan data: MariaDB`.
4. Konfigurasi bawaan cocok dengan XAMPP (user `root`, tanpa password, host `localhost`). Untuk mengganti, atur variabel lingkungan `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
5. Lihat isi tabel di phpMyAdmin: http://localhost/phpmyadmin, database `peminjaman_lab`.

Pengujian: `python -m unittest discover -s tests` (40 tes text file dan 19 tes database; tes database dilewati otomatis bila MariaDB mati dan memakai database terpisah `peminjaman_lab_uji`). Rincian rancangan ada di [docs/Database.md](docs/Database.md).

## Anggota Kelompok

| No | Nama | NIM |
|----|------|-----|
| 1 | Fajriyah Yulia Az Zahra | K3525005 |
| 2 | Sulthan Hafizh Putra Agung | K3525013 |
| 3 | Zahra Faizza Kuncoroningrum | K3525017 |
| 4 | Muzni Mubarok Salim | K3525036 |

Pembagian kontribusi ada di [docs/Pembagian_Tugas.md](docs/Pembagian_Tugas.md).

## Deskripsi Sistem

Semua aturan bisnis Proyek 1 tetap berlaku (alat tidak tersedia ditolak, maksimal 2 transaksi aktif, pengembalian sebagian, kondisi alat memengaruhi stok, larangan hapus data yang masih aktif, batas pinjam 7 hari). Ditambah dua aturan baru:

- **Konsistensi data.** Isi file dan isi memori selalu sama. Operasi yang ditolak aturan bisnis tidak menyentuh file. Bila penulisan file gagal, perubahan di memori dibatalkan.
- **Keterkaitan antarfile.** NIM dan kode alat di transaksi harus ada di file mahasiswa dan alat. ID transaksi, NIM, dan kode alat tidak boleh ganda, termasuk setelah program dijalankan ulang. Karena itu mahasiswa atau alat yang pernah tercatat dalam transaksi (termasuk yang sudah selesai) tidak dapat dihapus.

Tantangan yang dikerjakan: **A** pencarian fleksibel, **B** statistik, **C** pemeliharaan (`pemeliharaan.txt`), **D** log aktivitas (`log.txt`, mode append), **E** backup dan pemulihan, **F** ekspor laporan.

## Struktur Program

```text
├── main.py
├── README.md
├── data/                    file penyimpanan permanen (contoh: 4 mahasiswa (anggota kelompok), 10 alat, 3 transaksi)
│   ├── mahasiswa.txt
│   ├── alat.txt
│   ├── transaksi.txt
│   ├── detail_transaksi.txt
│   └── pemeliharaan.txt     (log.txt dibuat otomatis saat program dijalankan)
├── models/                  Mahasiswa, Alat, ItemPinjam, Transaksi, enum, validasi
├── managers/                koleksi di memori + aturan bisnis
│   ├── dasar.py             ManagerDasar: menyimpan, membatalkan bila gagal, mencatat log
│   ├── mahasiswa_manager.py
│   ├── alat_manager.py
│   └── transaksi_manager.py
├── storage/                 semua urusan file ada di sini
│   ├── file_teks.py         FileTeks: satu-satunya kode open()/with, try-except, split/join
│   ├── database.py          Database: konfigurasi dan koneksi MariaDB, membuat skema
│   ├── repositori.py        format tiap file, memuat dan menyimpan, validasi baris
│   ├── repositori_db.py     RepositoriDB: SQL (upsert, JOIN), transaksi, cermin ke txt
│   ├── log_aktivitas.py     Tantangan D
│   ├── backup.py            Tantangan E
│   └── laporan.py           Tantangan F
├── core/sistem.py           merakit semua objek dan memuat data
├── util/format.py           pembentuk tabel dan teks (dipakai Menu dan Laporan)
├── ui/Menu.py               antarmuka pengguna
├── sql/skema.sql            DDL tabel MariaDB
├── requirements.txt
├── tests/test_penyimpanan.py  40 pengujian text file
├── tests/test_database.py   19 pengujian database
├── backup/ dan laporan/     dibuat otomatis saat fitur dipakai
└── docs/                    dokumen desain, format file, UML, pengujian, review, refleksi
```

Alur baca/tulis: manager tidak pernah menyentuh file. Mereka memanggil `Repositori.simpan_*()`, dan hanya `FileTeks` yang membuka file. Dengan begitu kode baca/tulis tidak tersebar di menu.

## Format File

Satu baris satu data, kolom dipisahkan `|`. Baris kosong dan baris berawalan `#` diabaikan. Rincian lengkap ada di [docs/Format_File.md](docs/Format_File.md).

```text
mahasiswa.txt         NIM|nama|no_hp|status_aktif
alat.txt              kode|nama|kategori|kondisi|status
transaksi.txt         id|nim|tgl_pinjam|batas_kembali|status
detail_transaksi.txt  id|kode|status|kondisi|tgl_kembali
pemeliharaan.txt      kode|tgl_masuk
log.txt               [YYYY-MM-DD HH:MM] keterangan
```

Karena `|` adalah pemisah, isian teks tidak boleh memuatnya. Program menolak isian seperti itu.

## Cara Menjalankan

```bash
python main.py
```

Di Windows bisa memakai `py main.py`. Diperlukan Python 3.8 atau lebih baru, tanpa paket tambahan. Program memakai folder `data/` di samping `main.py`, jadi boleh dijalankan dari folder mana saja.

Untuk memulai dari data kosong, hapus isi folder `data/`. File akan dibuat ulang otomatis.

## Pengujian

```bash
python -m unittest discover -s tests -v
```

Hasil dan pemetaan ke skenario wajib ada di [docs/Hasil_Pengujian.md](docs/Hasil_Pengujian.md).

## Perilaku Penting

- Baris yang formatnya salah dilewati dengan peringatan saat program mulai. Baris itu hilang dari file pada penyimpanan berikutnya, tetapi salinan file asli otomatis diamankan di `backup/cadangan_otomatis_...` sebelum itu terjadi.
- Status turunan (ketersediaan alat, status aktif mahasiswa) dihitung ulang dari transaksi saat memuat. Selisih dengan isi file dilaporkan lalu dikoreksi.
- Penulisan file memakai file sementara lalu diganti sekaligus, sehingga file tidak setengah jadi bila terjadi kegagalan.
- Memulihkan backup selalu mengamankan kondisi saat ini ke folder `sebelum_pulih_...` terlebih dulu.
