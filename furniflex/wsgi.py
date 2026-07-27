"""
WSGI config for furniflex project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys
import shutil
import traceback
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "furniflex.settings")

try:
    # Path to original database in the project bundle
    BASE_DIR = Path(__file__).resolve().parent.parent
    original_db = BASE_DIR / "db.sqlite3"
    target_db = Path("/tmp/db.sqlite3")

    # Copy the pre-populated SQLite DB to /tmp if running on Vercel
    if os.environ.get("VERCEL") and original_db.exists():
        if not target_db.exists():
            try:
                shutil.copy2(original_db, target_db)
            except Exception as e:
                print("Failed to copy db.sqlite3 to /tmp:", e)

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

except Exception as e:
    # Catch any startup crash and display the traceback in the browser for debugging
    tb = traceback.format_exc()
    def error_app(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, headers)
        return [f"WSGI Bootstrap Error:\n\n{tb}".encode('utf-8')]
    application = error_app

# Vercel looks for `app` variable
app = application
