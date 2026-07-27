"""
WSGI config for furniflex project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "furniflex.settings")

application = get_wsgi_application()

# Vercel looks for `app` variable
app = application

# On Vercel, auto-run migrations since DB is in ephemeral /tmp
if os.environ.get("VERCEL"):
    from django.core.management import call_command
    call_command("migrate", "--run-syncdb", verbosity=0)
