import sys
import os

# Tambahkan parent folder ke sys.path agar Python bisa menemukan folder 'app'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import variabel 'app' yang sudah pasti ada di __init__.py
from app import app

# Vercel butuh variabel global bernama 'application'
application = app