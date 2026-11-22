#dikerjakan oleh
#Nama: Zahra Faizza Kuncoroningrum
#NIM: K3525017
#Kelas: B / Semester 3
#Angkatan: 2025

from datetime import datetime

from storage.file_teks import PenyimpananError

NAMA_FILE = "log.txt"


class LogAktivitas:
    """Riwayat aktivitas. Disimpan di list selama program berjalan dan ditambahkan
    ke akhir log.txt (mode append) sehingga log lama tidak pernah terhapus."""

    def __init__(self, file_teks):
        self.file = file_teks
        self.entri = []
        self.galat_terakhir = None

    def muat(self):
        self.entri = self.file.baca_baris_mentah(NAMA_FILE)

    def catat(self, pesan, waktu=None):
        waktu = waktu or datetime.now()
        pesan = " ".join(str(pesan).split())
        baris = f"[{waktu.strftime('%Y-%m-%d %H:%M')}] {pesan}"
        self.entri.append(baris)
        try:
            self.file.tambah(NAMA_FILE, baris)
        except PenyimpananError as e:
            # Kegagalan menulis log tidak boleh membatalkan operasi utama.
            self.galat_terakhir = e

    def terakhir(self, jumlah=25):
        return self.entri[-jumlah:]


class LogDB(LogAktivitas):
    """Log aktivitas yang juga disimpan di tabel log_aktivitas. File log.txt tetap
    ditambah (mode append), jadi riwayat ada di database sekaligus di text file."""

    def __init__(self, file_teks, database):
        super().__init__(file_teks)
        self.database = database

    def muat(self):
        try:
            conn = self.database.connect()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT DATE_FORMAT(waktu, '%Y-%m-%d %H:%i') AS w, pesan "
                                "FROM log_aktivitas ORDER BY id_log")
                    baris = [f"[{r['w']}] {r['pesan']}" for r in cur.fetchall()]
            finally:
                conn.close()
        except (PenyimpananError, Exception) as e:
            self.galat_terakhir = e
            baris = []
        if baris:
            self.entri = baris
        else:
            super().muat()

    def catat(self, pesan, waktu=None):
        waktu = waktu or datetime.now()
        super().catat(pesan, waktu)
        pesan = " ".join(str(pesan).split())[:500]
        try:
            conn = self.database.connect()
            try:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO log_aktivitas (waktu, pesan) VALUES (%s, %s)",
                                (waktu.strftime("%Y-%m-%d %H:%M:%S"), pesan))
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            self.galat_terakhir = e
