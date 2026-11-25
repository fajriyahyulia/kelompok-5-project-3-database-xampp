#dikerjakan oleh:
# Nama : Fajriyah Yulia Az Zahra
# NIM : K3525005

import os

from managers.mahasiswa_manager import MahasiswaManager
from managers.alat_manager import AlatManager
from managers.transaksi_manager import TransaksiManager
from storage.file_teks import FileTeks
from storage.repositori import Repositori
from storage.log_aktivitas import LogAktivitas, LogDB
from storage.backup import PengelolaBackup
from storage.laporan import PembuatLaporan


class Sistem:
    """Merakit seluruh objek aplikasi dan memuat data dari file.

    Menu hanya berurusan dengan kelas ini, sehingga Menu tidak perlu tahu cara
    membuat manager atau di mana file disimpan. Tes juga memakainya langsung dengan
    folder sementara.
    """

    def __init__(self, folder_data, folder_backup=None, folder_laporan=None, database=None):
        induk = os.path.dirname(os.path.abspath(folder_data))
        self.file = FileTeks(folder_data)
        self.mhs_mgr = MahasiswaManager()
        self.alat_mgr = AlatManager()
        self.trx_mgr = TransaksiManager(self.mhs_mgr, self.alat_mgr)
        self.database = database
        if database is None:
            self.cermin = None
            self.log = LogAktivitas(self.file)
            self.repositori = Repositori(self.file)
        else:
            # Mode database: data utama ada di MariaDB, text file menjadi cermin untuk
            # backup dan pemulihan.
            database.pastikan_skema()
            from storage.repositori_db import RepositoriDB
            self.cermin = Repositori(self.file)
            self.log = LogDB(self.file, database)
            self.repositori = RepositoriDB(database, self.cermin)
        self.repositori.hubungkan(self.mhs_mgr, self.alat_mgr, self.trx_mgr, self.log)
        self.backup = PengelolaBackup(self.file, folder_backup or os.path.join(induk, "backup"),
                                      segarkan=self.cermin.simpan_semua if self.cermin else None)
        self.laporan = PembuatLaporan(folder_laporan or os.path.join(induk, "laporan"),
                                      self.mhs_mgr, self.alat_mgr, self.trx_mgr)
        self.peringatan = []
        self.cadangan_otomatis = None
        if database is not None and self.repositori.kosong():
            # Database baru dan masih kosong: isi dari data/*.txt (migrasi pertama kali).
            self.impor_dari_txt()
        else:
            self.muat()
        if self.peringatan:
            # Ada baris yang dilewati: simpan salinan file asli sebelum penyimpanan
            # berikutnya menimpanya, supaya tidak ada data yang hilang diam-diam.
            self.cadangan_otomatis = self.backup.buat("cadangan_otomatis")

    def muat(self):
        """Baca (atau baca ulang) semua data dari file. Mengembalikan daftar peringatan."""
        self.peringatan = self.repositori.muat()
        self.log.muat()
        return self.peringatan

    @property
    def mode(self):
        return "MariaDB" if self.database is not None else "text file"

    def impor_dari_txt(self):
        """Baca data/*.txt lalu tulis ke database (mode database), atau cukup baca ulang
        (mode text file). Dipakai untuk migrasi awal dan setelah pemulihan dari backup."""
        if self.database is None:
            return self.muat()
        self.peringatan = self.cermin.muat()
        self.repositori.simpan_semua()
        self.log.muat()
        return self.peringatan

    def simpan_semua(self):
        self.repositori.simpan_semua()
