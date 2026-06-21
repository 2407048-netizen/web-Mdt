import sys
import os
# Wajib agar Vercel bisa melihat folder 'app'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
application = create_app()