#dikerjakan oleh:
# Nama : Fajriyah Yulia Az Zahra
# NIM : K3525005

import os

import pymysql

from storage.file_teks import PenyimpananError

BERKAS_SKEMA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sql", "skema.sql")


class Database:
    """Satu-satunya tempat konfigurasi dan pembuatan koneksi MariaDB.

    Nilai bawaan cocok dengan XAMPP (user root tanpa password). Semuanya bisa diganti
    lewat variabel lingkungan DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, dan DB_NAME.
    """

    def __init__(self, **ubah):
        self.config = {
            "host": os.environ.get("DB_HOST", "localhost"),
            "port": int(os.environ.get("DB_PORT", "3306")),
            "user": os.environ.get("DB_USER", "root"),
            "password": os.environ.get("DB_PASSWORD", ""),
            "database": os.environ.get("DB_NAME", "peminjaman_lab"),
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": False,
            "connect_timeout": 5,
        }
        self.config.update(ubah)

    def connect(self):
        try:
            return pymysql.connect(**self.config)
        except pymysql.MySQLError as e:
            raise PenyimpananError(f"Tidak dapat terhubung ke database: {e}") from e

    def pastikan_skema(self):
        """Buat database dan tabel bila belum ada (isi sql/skema.sql). Aman dipanggil berulang."""
        nama = self.config["database"]
        awal = dict(self.config)
        awal.pop("database")
        try:
            with open(BERKAS_SKEMA, encoding="utf-8") as f:
                baris = [b for b in f.read().splitlines() if not b.strip().startswith("--")]
            perintah = [p.strip() for p in "\n".join(baris).split(";") if p.strip()]
            conn = pymysql.connect(**awal)
            try:
                with conn.cursor() as cur:
                    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{nama}` "
                                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    cur.execute(f"USE `{nama}`")
                    for p in perintah:
                        if p.upper().startswith(("CREATE DATABASE", "USE ")):
                            continue
                        cur.execute(p)
                conn.commit()
            finally:
                conn.close()
        except (pymysql.MySQLError, OSError) as e:
            raise PenyimpananError(f"Gagal menyiapkan skema database: {e}") from e