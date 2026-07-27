import sys
import os
import traceback

try:
    from furniflex.wsgi import app
except Exception as e:
    tb = traceback.format_exc()
    def app(environ, start_response):
        status = '200 OK'
        headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, headers)
        err_msg = f"DJANGO STARTUP EXCEPTION:\n\n{tb}"
        return [err_msg.encode('utf-8')]
