import sys
import os

# PENTING: Tambahkan folder root project ke Python Path
# Agar api/index.py bisa "melihat" folder app yang ada di luar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app

# Vercel membutuhkan variabel bernama 'application'
application = create_app()