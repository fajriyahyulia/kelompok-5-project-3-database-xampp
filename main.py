#dikerjakan oleh:
# Nama : Fajriyah Yulia Az Zahra
# NIM : K3525005

import os

from core.sistem import Sistem
from storage.file_teks import PenyimpananError
from ui.Menu import Menu

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))


def siapkan_database():
    if os.environ.get("PEMINJAMAN_MODE", "db").lower() == "txt":
        return None
    try:
        from storage.database import Database
    except ImportError:
        print("[!] PyMySQL belum terpasang (pip install pymysql). Memakai mode text file.")
        return None
    database = Database()
    try:
        database.pastikan_skema()
    except PenyimpananError as e:
        print(f"[!] {e}\n    Nyalakan MySQL di XAMPP untuk memakai database. Memakai mode text file.")
        return None
    return database


if __name__ == "__main__":
    try:
        sistem = Sistem(
            folder_data=os.path.join(FOLDER_PROYEK, "data"),
            folder_backup=os.path.join(FOLDER_PROYEK, "backup"),
            folder_laporan=os.path.join(FOLDER_PROYEK, "laporan"),
            database=siapkan_database(),
        )
    except PenyimpananError as e:
        print(f"[!] Data tidak dapat dibaca, program dihentikan: {e}")
    else:
        Menu(sistem).jalankan()