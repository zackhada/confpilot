"""ASGI entry point: ``uvicorn confpilot.main:app``."""

from confpilot.app import create_app

app = create_app()
