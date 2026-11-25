#dikerjakan oleh:
# Nama : Fajriyah Yulia Az Zahra
# NIM : K3525005

import pymysql

from storage.file_teks import PenyimpananError
from storage.repositori import (Repositori, FILE_MAHASISWA, FILE_ALAT, FILE_TRANSAKSI,
                                FILE_DETAIL, FILE_PEMELIHARAAN, KOSONG)

# Satu query per "file" lama. Hasilnya dibuat berbentuk daftar teks yang sama persis
# dengan baris text file, sehingga validasi dan sinkronisasi di Repositori dipakai ulang.
SQL_BACA = {
    FILE_MAHASISWA: "SELECT nim, nama, no_hp, status_aktif FROM mahasiswa ORDER BY id_mahasiswa",
    FILE_ALAT: "SELECT kode, nama, kategori, kondisi, status FROM alat ORDER BY id_alat",
    FILE_PEMELIHARAAN: """SELECT a.kode, CAST(p.tgl_masuk AS CHAR) AS tgl
                          FROM pemeliharaan p JOIN alat a ON a.id_alat = p.id_alat
                          ORDER BY p.id_pemeliharaan""",
    FILE_TRANSAKSI: """SELECT t.id_transaksi, m.nim, CAST(t.tgl_pinjam AS CHAR) AS tgl,
                              CAST(t.batas_kembali AS CHAR) AS batas, t.status
                       FROM transaksi t JOIN mahasiswa m ON m.id_mahasiswa = t.id_mahasiswa
                       ORDER BY t.id_transaksi""",
    FILE_DETAIL: """SELECT d.id_transaksi, a.kode, d.status, COALESCE(d.kondisi, '-') AS kondisi,
                           COALESCE(CAST(d.tgl_kembali AS CHAR), '-') AS tgl
                    FROM detail_transaksi d JOIN alat a ON a.id_alat = d.id_alat
                    ORDER BY d.id_detail""",
}
ISTILAH = {f: f"tabel {f[:-4]}" for f in (FILE_MAHASISWA, FILE_ALAT, FILE_TRANSAKSI,
                                           FILE_DETAIL, FILE_PEMELIHARAAN)}


def _tidak_ada(daftar):
    """Potongan SQL 'NOT IN (...)' untuk daftar kunci, atau (None, []) bila daftar kosong."""
    if not daftar:
        return None, []
    return ", ".join(["%s"] * len(daftar)), list(daftar)


class RepositoriDB(Repositori):
    """Repositori yang menyimpan ke MariaDB. Antarmukanya sama dengan Repositori text file
    (hubungkan, muat, simpan_mahasiswa, simpan_alat, simpan_semua), sehingga manager tidak
    perlu tahu data disimpan di mana.

    Setiap simpan_*() berjalan dalam satu transaksi: commit bila semua berhasil, rollback
    bila ada yang gagal, lalu PenyimpananError dilempar agar manager membatalkan perubahan
    di memori (Aturan 7). Setelah commit berhasil, isi database dicerminkan ke text file
    (data/*.txt) supaya backup, pemulihan, dan penyimpanan text file tetap berfungsi.
    """

    def __init__(self, database, cermin=None):
        super().__init__(file_teks=None)
        self.database = database
        self.cermin = cermin
        self.galat_cermin = None

    def hubungkan(self, mhs_mgr, alat_mgr, trx_mgr, log=None):
        super().hubungkan(mhs_mgr, alat_mgr, trx_mgr, log)
        if self.cermin is not None:
            self.cermin.mhs_mgr, self.cermin.alat_mgr, self.cermin.trx_mgr = mhs_mgr, alat_mgr, trx_mgr

    # ------------------------------------------------------------------
    # Memuat
    # ------------------------------------------------------------------
    def kosong(self):
        conn = self.database.connect()
        try:
            with conn.cursor() as cur:
                total = 0
                for tabel in ("mahasiswa", "alat", "transaksi"):
                    cur.execute(f"SELECT COUNT(*) AS n FROM {tabel}")
                    total += cur.fetchone()["n"]
            return total == 0
        except pymysql.MySQLError as e:
            raise PenyimpananError(f"Gagal membaca database: {e}") from e
        finally:
            conn.close()

    def _baca(self, nama, kolom, header):
        conn = self.database.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(SQL_BACA[nama])
                hasil = [[str(v) for v in baris.values()] for baris in cur.fetchall()]
        except pymysql.MySQLError as e:
            raise PenyimpananError(f"Gagal membaca {ISTILAH[nama]}: {e}") from e
        finally:
            conn.close()
        return list(enumerate(hasil, start=1))

    def muat(self):
        peringatan = super().muat()
        self.peringatan = []
        for p in peringatan:
            for lama, baru in ISTILAH.items():
                p = p.replace(lama, baru)
            self.peringatan.append(p)
        return self.peringatan

    # ------------------------------------------------------------------
    # Menyimpan
    # ------------------------------------------------------------------
    def _transaksi(self, kerja):
        conn = self.database.connect()
        try:
            with conn.cursor() as cur:
                kerja(cur)
            conn.commit()
        except pymysql.MySQLError as e:
            conn.rollback()
            raise PenyimpananError(f"Gagal menyimpan ke database: {e}") from e
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        self._cerminkan()

    def _cerminkan(self):
        if self.cermin is None:
            return
        try:
            self.cermin.simpan_semua()
            self.galat_cermin = None
        except PenyimpananError as e:
            self.galat_cermin = e

    def _hapus_yang_hilang(self, cur, tabel, kolom, ada):
        potongan, nilai = _tidak_ada(ada)
        if potongan is None:
            cur.execute(f"DELETE FROM {tabel}")
        else:
            cur.execute(f"DELETE FROM {tabel} WHERE {kolom} NOT IN ({potongan})", nilai)

    def _tulis_mahasiswa(self, cur):
        transaksi = self.trx_mgr.data
        mahasiswa = list(self.mhs_mgr.data.values())
        self._hapus_yang_hilang(cur, "mahasiswa", "nim", [m.nim for m in mahasiswa])
        for m in mahasiswa:
            cur.execute(
                """INSERT INTO mahasiswa (nim, nama, no_hp, status_aktif) VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE nama = VALUES(nama), no_hp = VALUES(no_hp),
                                           status_aktif = VALUES(status_aktif)""",
                (m.nim, m.nama, m.no_hp, m.status_aktif(transaksi)))

    def _tulis_alat(self, cur):
        alat = list(self.alat_mgr.data.values())
        potongan, nilai = _tidak_ada(list(self.alat_mgr.pemeliharaan))
        if potongan is None:
            cur.execute("DELETE FROM pemeliharaan")
        else:
            cur.execute("DELETE p FROM pemeliharaan p JOIN alat a ON a.id_alat = p.id_alat "
                        f"WHERE a.kode NOT IN ({potongan})", nilai)
        self._hapus_yang_hilang(cur, "alat", "kode", [a.kode for a in alat])
        for a in alat:
            cur.execute(
                """INSERT INTO alat (kode, nama, kategori, kondisi, status) VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE nama = VALUES(nama), kategori = VALUES(kategori),
                                           kondisi = VALUES(kondisi), status = VALUES(status)""",
                (a.kode, a.nama, a.kategori, a.kondisi.teks, a.status_teks()))
        for kode, tgl in self.alat_mgr.pemeliharaan.items():
            cur.execute(
                "INSERT INTO pemeliharaan (id_alat, tgl_masuk) SELECT id_alat, %s FROM alat WHERE kode = %s "
                "ON DUPLICATE KEY UPDATE tgl_masuk = VALUES(tgl_masuk)", (str(tgl), kode))

    def _tulis_transaksi(self, cur):
        daftar = self.trx_mgr.data
        potongan, nilai = _tidak_ada([f"{t.id_transaksi}|{i.alat.kode}" for t in daftar for i in t.daftar_item])
        if potongan is None:
            cur.execute("DELETE FROM detail_transaksi")
        else:
            cur.execute("DELETE d FROM detail_transaksi d JOIN alat a ON a.id_alat = d.id_alat "
                        f"WHERE CONCAT(d.id_transaksi, '|', a.kode) NOT IN ({potongan})", nilai)
        self._hapus_yang_hilang(cur, "transaksi", "id_transaksi", [t.id_transaksi for t in daftar])
        for t in daftar:
            cur.execute(
                """INSERT INTO transaksi (id_transaksi, id_mahasiswa, tgl_pinjam, batas_kembali, status)
                   SELECT %s, id_mahasiswa, %s, %s, %s FROM mahasiswa WHERE nim = %s
                   ON DUPLICATE KEY UPDATE id_mahasiswa = VALUES(id_mahasiswa),
                       tgl_pinjam = VALUES(tgl_pinjam), batas_kembali = VALUES(batas_kembali),
                       status = VALUES(status)""",
                (t.id_transaksi, str(t.tanggal_pinjam), str(t.batas_kembali), t.status.teks,
                 t.mahasiswa.nim))
            for item in t.daftar_item:
                if item.sudah_kembali:
                    status, kondisi, tgl = "dikembalikan", item.kondisi_kembali.teks, str(item.tanggal_kembali)
                else:
                    status, kondisi, tgl = "dipinjam", None, None
                cur.execute(
                    """INSERT INTO detail_transaksi (id_transaksi, id_alat, status, kondisi, tgl_kembali)
                       SELECT %s, id_alat, %s, %s, %s FROM alat WHERE kode = %s
                       ON DUPLICATE KEY UPDATE status = VALUES(status), kondisi = VALUES(kondisi),
                                               tgl_kembali = VALUES(tgl_kembali)""",
                    (t.id_transaksi, status, kondisi, tgl, item.alat.kode))

    def simpan_mahasiswa(self):
        self._transaksi(self._tulis_mahasiswa)

    def simpan_alat(self):
        """Alat dan pemeliharaan selalu ditulis bersama karena saling terkait."""
        self._transaksi(self._tulis_alat)

    def simpan_semua(self):
        """Dipakai setelah transaksi peminjaman: mahasiswa, alat, dan transaksi berubah
        sekaligus, jadi semuanya diganti dalam satu transaksi database."""
        def kerja(cur):
            self._tulis_mahasiswa(cur)
            self._tulis_alat(cur)
            self._tulis_transaksi(cur)
        self._transaksi(kerja)