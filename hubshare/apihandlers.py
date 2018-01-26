"""Handlers for the REST API"""
import os, json
from .handlers import BaseHandler
from jupyter_client.jsonutil import date_default

class APIHandler(BaseHandler):

    @property
    def hubshare_manager(self):
        return self.settings['hubshare_manager']


class ContentsHandler(APIHandler):

    urls = ['/dir']

    def get(self):
        path = 'hubshare'
        model = self.hubshare_manager.get(path=path, content=True,
                                           type='directory')

        self.write(json.dumps(model, default=date_default))

default_handlers = [
    ContentsHandler
]
