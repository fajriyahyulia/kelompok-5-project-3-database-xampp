#dikerjakan oleh:
# Nama : Fajriyah Yulia Az Zahra
# NIM : K3525005

import os
import shutil
import tempfile
import unittest
from unittest import mock

import pymysql

from core.sistem import Sistem
from models.alat import Alat
from models.enums import KondisiAlat
from models.mahasiswa import Mahasiswa
from storage.database import Database
from storage.file_teks import PenyimpananError

FOLDER_PROYEK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMA_DB_UJI = "peminjaman_lab_uji"


def database_uji():
    return Database(database=NAMA_DB_UJI)


def mariadb_menyala():
    try:
        pymysql.connect(host=Database().config["host"], port=Database().config["port"],
                        user=Database().config["user"], password=Database().config["password"],
                        connect_timeout=2).close()
        return True
    except pymysql.MySQLError:
        return False


@unittest.skipUnless(mariadb_menyala(), "MariaDB tidak menyala, tes database dilewati")
class DasarDB(unittest.TestCase):
    salin_data_contoh = True

    def setUp(self):
        self.db = database_uji()
        conn = pymysql.connect(host=self.db.config["host"], port=self.db.config["port"],
                               user=self.db.config["user"], password=self.db.config["password"])
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {NAMA_DB_UJI}")
        conn.commit()
        conn.close()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.folder = os.path.join(self.tmp, "data")
        if self.salin_data_contoh:
            shutil.copytree(os.path.join(FOLDER_PROYEK, "data"), self.folder)
        self.s = self.buka()

    def buka(self):
        return Sistem(self.folder, database=database_uji())

    def sql(self, query, args=None):
        conn = self.db.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(query, args)
                hasil = cur.fetchall()
            conn.commit()
            return hasil
        finally:
            conn.close()


class TestMigrasiAwal(DasarDB):
    def test_database_kosong_diisi_dari_text_file(self):
        self.assertEqual(self.s.mode, "MariaDB")
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM mahasiswa")[0]["n"], 4)
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM alat")[0]["n"], 10)
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM transaksi")[0]["n"], 3)
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM detail_transaksi")[0]["n"], 7)
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM pemeliharaan")[0]["n"], 1)
        self.assertEqual(self.s.peringatan, [])

    def test_migrasi_hanya_sekali(self):
        self.s.mhs_mgr.tambah(Mahasiswa("K3525099", "Tamu Baru", "081200000000"))
        s2 = self.buka()
        self.assertIn("K3525099", s2.mhs_mgr.data)
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM mahasiswa")[0]["n"], 5)

    def test_skema_aman_dijalankan_berulang(self):
        self.db.pastikan_skema()
        self.db.pastikan_skema()
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM mahasiswa")[0]["n"], 4)


class TestPersistenDB(DasarDB):
    def test_tambah_mahasiswa_dan_alat_bertahan_setelah_restart(self):
        self.s.mhs_mgr.tambah(Mahasiswa("K3525099", "Tamu Baru", "081200000000"))
        self.s.alat_mgr.tambah(Alat("A011", "Stopwatch", "perangkat elektronika"))
        s2 = self.buka()
        self.assertEqual(s2.mhs_mgr.get("K3525099").nama, "Tamu Baru")
        self.assertEqual(s2.alat_mgr.get("A011").nama, "Stopwatch")
        self.assertEqual(s2.peringatan, [])

    def test_transaksi_dan_pengembalian_bertahan(self):
        trx = self.s.trx_mgr.buat_transaksi("K3525005", ["A006"])
        self.s.trx_mgr.proses_pengembalian(trx.id_transaksi, "A006", KondisiAlat.RUSAK_RINGAN)
        s2 = self.buka()
        t2 = s2.trx_mgr.get(trx.id_transaksi)
        self.assertEqual(t2.status, trx.status)
        self.assertEqual(s2.alat_mgr.get("A006").kondisi, KondisiAlat.RUSAK_RINGAN)
        self.assertFalse(s2.alat_mgr.get("A006").is_tersedia())
        self.assertEqual(s2.peringatan, [])
        self.assertEqual(s2.trx_mgr.buat_transaksi("K3525017", ["A007"]).id_transaksi, "T005")

    def test_hapus_data_tanpa_riwayat_ikut_hilang_dari_database(self):
        self.s.mhs_mgr.tambah(Mahasiswa("K3525099", "Tamu Baru", "081200000000"))
        self.s.alat_mgr.tambah(Alat("A011", "Stopwatch", "perangkat elektronika"))
        self.s.mhs_mgr.hapus("K3525099", self.s.trx_mgr.data)
        self.s.alat_mgr.hapus("A011", self.s.trx_mgr.data)
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM mahasiswa WHERE nim='K3525099'")[0]["n"], 0)
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM alat WHERE kode='A011'")[0]["n"], 0)

    def test_data_beririwayat_tetap_ditolak_hapus(self):
        with self.assertRaises(ValueError):
            self.s.mhs_mgr.hapus("K3525005", self.s.trx_mgr.data)
        self.assertIn("K3525005", self.s.mhs_mgr.data)

    def test_id_detail_stabil_antar_penyimpanan(self):
        sebelum = self.sql("SELECT id_detail, id_transaksi FROM detail_transaksi ORDER BY id_detail")
        self.s.simpan_semua()
        self.s.simpan_semua()
        self.assertEqual(self.sql("SELECT id_detail, id_transaksi FROM detail_transaksi ORDER BY id_detail"), sebelum)


class TestIntegritasDB(DasarDB):
    def test_foreign_key_menolak_hapus_mahasiswa_bertransaksi(self):
        with self.assertRaises(pymysql.err.IntegrityError):
            self.sql("DELETE FROM mahasiswa WHERE nim = 'K3525005'")

    def test_unique_menolak_nim_ganda(self):
        with self.assertRaises(pymysql.err.IntegrityError):
            self.sql("INSERT INTO mahasiswa (nim, nama, no_hp, status_aktif) "
                     "VALUES ('K3525005', 'Ganda', '081200000000', 'aktif')")

    def test_check_menolak_kondisi_tidak_dikenal(self):
        with self.assertRaises(pymysql.err.Error):
            self.sql("UPDATE alat SET kondisi = 'hancur' WHERE kode = 'A001'")

    def test_gagal_simpan_membatalkan_perubahan_di_memori(self):
        with mock.patch.object(Database, "connect", side_effect=PenyimpananError("db mati")):
            with self.assertRaises(PenyimpananError):
                self.s.mhs_mgr.tambah(Mahasiswa("K3525099", "Tamu Baru", "081200000000"))
        self.assertNotIn("K3525099", self.s.mhs_mgr.data)

    def test_gagal_di_tengah_transaksi_database_di_rollback(self):
        self.s.mhs_mgr.tambah(Mahasiswa("K3525099", "Tamu Baru", "081200000000"), simpan=False)
        galat = pymysql.err.OperationalError(2013, "koneksi putus")
        with mock.patch.object(type(self.s.repositori), "_tulis_alat", side_effect=galat):
            with self.assertRaises(PenyimpananError):
                self.s.repositori.simpan_semua()
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM mahasiswa WHERE nim='K3525099'")[0]["n"], 0)

    def test_status_turunan_dikoreksi_bila_database_diubah_manual(self):
        self.sql("UPDATE alat SET status = 'tersedia' WHERE kode = 'A001'")
        s2 = self.buka()
        self.assertFalse(s2.alat_mgr.get("A001").is_tersedia())
        self.assertTrue(any("A001" in p and "dikoreksi" in p for p in s2.peringatan))


class TestTextFileTetapAda(DasarDB):
    def test_text_file_dicerminkan_setelah_setiap_simpan(self):
        self.s.mhs_mgr.tambah(Mahasiswa("K3525099", "Tamu Baru", "081200000000"))
        with open(os.path.join(self.folder, "mahasiswa.txt"), encoding="utf-8") as f:
            self.assertIn("K3525099|Tamu Baru", f.read())

    def test_log_masuk_database_dan_log_txt(self):
        self.s.log.catat("uji log database")
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM log_aktivitas WHERE pesan='uji log database'")[0]["n"], 1)
        with open(os.path.join(self.folder, "log.txt"), encoding="utf-8") as f:
            self.assertIn("uji log database", f.read())
        self.assertTrue(any("uji log database" in e for e in self.buka().log.entri))

    def test_backup_dan_pemulihan_mengembalikan_database(self):
        nama = self.s.backup.buat()
        self.s.mhs_mgr.tambah(Mahasiswa("K3525099", "Tamu Baru", "081200000000"))
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM mahasiswa")[0]["n"], 5)
        self.s.backup.pulihkan(nama)
        self.s.impor_dari_txt()
        self.assertEqual(self.sql("SELECT COUNT(*) n FROM mahasiswa")[0]["n"], 4)
        self.assertNotIn("K3525099", self.s.mhs_mgr.data)

    def test_backup_memuat_data_terbaru_dari_database(self):
        self.s.mhs_mgr.tambah(Mahasiswa("K3525099", "Tamu Baru", "081200000000"))
        nama = self.s.backup.buat()
        with open(os.path.join(self.s.backup.folder_backup, nama, "mahasiswa.txt"), encoding="utf-8") as f:
            self.assertIn("K3525099", f.read())

    def test_laporan_tetap_diekspor_ke_text_file(self):
        jalur = self.s.laporan.alat_dipinjam()
        self.assertTrue(os.path.exists(jalur))
        self.assertTrue(jalur.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()
