import sys
import os

# Trik agar Python bisa menemukan folder 'app' yang ada di parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    # Import aplikasi Flask dari folder app
    from app import app
except ImportError as e:
    print(f"Error: Gagal import app. Detail: {e}")
    raise e

# Vercel WAJIB melihat variabel bernama 'application' atau 'app' di level global
application = app