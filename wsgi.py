"""WSGI entry point for production servers (gunicorn / Render)."""
from src.app import app

application = app  # some WSGI servers look for `application`
