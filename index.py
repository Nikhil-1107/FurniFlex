import sys
import os

def app(environ, start_response):
    status = '200 OK'
    headers = [('Content-Type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    info = f"Hello World from Vercel Python!\nPython Version: {sys.version}\nCWD: {os.getcwd()}"
    return [info.encode('utf-8')]
