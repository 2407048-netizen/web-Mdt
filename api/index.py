import sys
import os

# Tambahkan root folder ke PATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    # Coba import 'app' dulu
    from app import app as application
    print("Success: Imported 'app' from app/__init__.py")
except ImportError:
    try:
        # Jika gagal, coba import 'application'
        from app import application
        print("Success: Imported 'application' from app/__init__.py")
    except ImportError:
        # Jika masih gagal, tampilkan error jelas
        raise ImportError("Error: Tidak ditemukan 'app' atau 'application' di app/__init__.py. Cek file tersebut!")

# Vercel butuh variabel bernama 'application'