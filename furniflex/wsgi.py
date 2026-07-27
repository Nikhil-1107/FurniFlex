"""
WSGI config for furniflex project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import shutil
from pathlib import Path
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "furniflex.settings")

# Path to original database in the project bundle
BASE_DIR = Path(__file__).resolve().parent.parent
original_db = BASE_DIR / "db.sqlite3"
target_db = Path("/tmp/db.sqlite3")

# Copy the pre-populated SQLite DB to /tmp if running on Vercel
if os.environ.get("VERCEL") and original_db.exists():
    if not target_db.exists():
        try:
            shutil.copy2(original_db, target_db)
            print("Successfully copied db.sqlite3 to /tmp")
        except Exception as e:
            print("Failed to copy db.sqlite3 to /tmp:", e)

application = get_wsgi_application()

# Vercel looks for `app` variable
app = application
