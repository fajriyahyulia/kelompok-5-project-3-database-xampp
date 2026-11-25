CREATE DATABASE IF NOT EXISTS peminjaman_lab CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE peminjaman_lab;

CREATE TABLE IF NOT EXISTS mahasiswa (
    id_mahasiswa INT AUTO_INCREMENT PRIMARY KEY,
    nim VARCHAR(15) NOT NULL UNIQUE,
    nama VARCHAR(100) NOT NULL,
    no_hp VARCHAR(20) NOT NULL,
    status_aktif VARCHAR(15) NOT NULL DEFAULT 'tidak aktif',
    CONSTRAINT ck_mahasiswa_status CHECK (status_aktif IN ('aktif', 'tidak aktif'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS alat (
    id_alat INT AUTO_INCREMENT PRIMARY KEY,
    kode VARCHAR(15) NOT NULL UNIQUE,
    nama VARCHAR(100) NOT NULL,
    kategori VARCHAR(100) NOT NULL,
    kondisi VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    CONSTRAINT ck_alat_kondisi CHECK (kondisi IN ('baik', 'rusak ringan', 'rusak berat')),
    CONSTRAINT ck_alat_status CHECK (status IN ('tersedia', 'dipinjam', 'tidak tersedia'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pemeliharaan (
    id_pemeliharaan INT AUTO_INCREMENT PRIMARY KEY,
    id_alat INT NOT NULL UNIQUE,
    tgl_masuk DATE NOT NULL,
    CONSTRAINT fk_pemeliharaan_alat
        FOREIGN KEY (id_alat) REFERENCES alat(id_alat)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transaksi (
    id_transaksi VARCHAR(15) PRIMARY KEY,
    id_mahasiswa INT NOT NULL,
    tgl_pinjam DATE NOT NULL,
    batas_kembali DATE NOT NULL,
    status VARCHAR(25) NOT NULL,
    CONSTRAINT ck_transaksi_status CHECK (status IN ('dipinjam', 'sebagian dikembalikan', 'selesai')),
    CONSTRAINT fk_transaksi_mahasiswa
        FOREIGN KEY (id_mahasiswa) REFERENCES mahasiswa(id_mahasiswa)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS detail_transaksi (
    id_detail INT AUTO_INCREMENT PRIMARY KEY,
    id_transaksi VARCHAR(15) NOT NULL,
    id_alat INT NOT NULL,
    status VARCHAR(15) NOT NULL,
    kondisi VARCHAR(20) NULL,
    tgl_kembali DATE NULL,
    CONSTRAINT uq_detail UNIQUE (id_transaksi, id_alat),
    CONSTRAINT ck_detail_status CHECK (status IN ('dipinjam', 'dikembalikan')),
    CONSTRAINT fk_detail_transaksi
        FOREIGN KEY (id_transaksi) REFERENCES transaksi(id_transaksi)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_detail_alat
        FOREIGN KEY (id_alat) REFERENCES alat(id_alat)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS log_aktivitas (
    id_log INT AUTO_INCREMENT PRIMARY KEY,
    waktu DATETIME NOT NULL,
    pesan VARCHAR(500) NOT NULL
) ENGINE=InnoDB;
