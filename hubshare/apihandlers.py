"""Handlers for the REST API"""
import os, json
from notebook.services.contents.handlers import ContentsHandler
from notebook.base.handlers import path_regex
from jupyter_client.jsonutil import date_default

class PublicContentsHandler(ContentsHandler):
    # URLS handled by this handler.
    urls = ['/dir']


default_handlers = [
    PublicContentsHandler
]
