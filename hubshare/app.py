#!/usr/bin/env python3
"""
The HubShare main application.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from datetime import datetime
import logging
import os
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader
from tornado.httpserver import HTTPServer
from tornado.log import app_log, access_log, gen_log
from tornado.ioloop import IOLoop
from tornado import web

from traitlets.config import catch_config_error
from traitlets import (
    Bool, Dict, Integer, List, Unicode,
    default,
)

from jupyterhub.log import CoroutineLogFormatter, log_request
from jupyterhub.services.auth import HubAuth
from jupyterhub.utils import url_path_join

from . import handlers, apihandlers
from .manager import HubShareManager

from jupyter_core.application import JupyterApp
from jupyter_server.serverapp import (
    load_handlers,
    ServerWebApplication,
    ServerApp
)

ROOT = os.path.dirname(__file__)
DEFAULT_STATIC_FILES_PATH = os.path.join(ROOT, 'static')
DEFAULT_TEMPLATE_PATH_LIST = [os.path.join(ROOT, 'templates')]

class UnicodeFromEnv(Unicode):
    """A Unicode trait that gets its default value from the environment

    Use .tag(env='VARNAME') to specify the environment variable to use.
    """
    def default(self, obj=None):
        env_key = self.metadata.get('env')
        if env_key in os.environ:
            return os.environ[env_key]
        else:
            return self.default_value


class HubShare(ServerApp):
    """The HubShare application"""
    @property
    def version(self):
        import pkg_resources
        return pkg_resources.get_distribution('hubshare').version

    description = __doc__
    config_file = Unicode('hubshare_config.py',
        help="The config file to load",
    ).tag(config=True)
    generate_config = Bool(False,
        help="Generate default config file",
    ).tag(config=True)

    base_url = UnicodeFromEnv('/services/hubshare/').tag(
        env='JUPYTERHUB_SERVICE_PREFIX',
        config=True)
    hub_api_url = UnicodeFromEnv('http://127.0.0.1:8081/hub/api/').tag(
        env='JUPYTERHUB_API_URL',
        config=True)
    hub_api_token = UnicodeFromEnv('').tag(
        env='JUPYTERHUB_API_TOKEN',
        config=True,
    )
    hub_base_url = UnicodeFromEnv('http://127.0.0.1:8000/').tag(
        env='JUPYTERHUB_BASE_URL',
        config=True,
    )

    classes = List([
        HubShareManager
    ])

    ip = Unicode('127.0.0.1').tag(config=True)

    @default('ip')
    def _ip_default(self):
        url_s = os.environ.get('JUPYTERHUB_SERVICE_URL')
        if not url_s:
            return '127.0.0.1'
        url = urlparse(url_s)
        return url.hostname

    port = Integer(9090).tag(config=True)

    @default('port')
    def _port_default(self):
        url_s = os.environ.get('JUPYTERHUB_SERVICE_URL')
        if not url_s:
            return 9090
        url = urlparse(url_s)
        return url.port

    @property
    def static_file_path(self):
        """return extra paths + the default location"""
        return self.extra_static_paths + [DEFAULT_STATIC_FILES_PATH]

    @property
    def template_file_path(self):
        """return extra paths + the default locations"""
        return self.extra_template_paths + DEFAULT_TEMPLATE_PATH_LIST

    def init_db(self):
        """Initialize the HubShare database"""
        self.db = None
        self.tornado_settings["db"] = self.db

    def init_hub_auth(self):
        """Initialize hub authentication"""
        self.hub_auth = HubAuth(api_token=self.token)
        self.tornado_settings["hub_auth"] = self.hub_auth

    def init_extra_settings(self):
        self.tornado_settings["logout_url"] = url_path_join(
            self.hub_base_url, 'hub/logout')
        self.tornado_settings['contents_manager'] = HubShareManager(
            parent=self,
            log=self.log
        )

    def init_hubshare_handlers(self):
        """Load hubshare's tornado request handlers"""
        handlers_ = [] 
        for handler in handlers.default_handlers + apihandlers.default_handlers:
            for url in handler.urls:
                handlers_.append((url_path_join(self.base_url, url), handler))
        handlers_.append((r'.*', handlers.Template404))
        self.web_app.add_handlers('.*$', handlers_)

    @catch_config_error
    def initialize(self, argv=None):
        # This method hopefully won't be needed is jupyter_server is completely 
        # configurable and granular

        # Prevent the browser from opening.
        self.open_browser = False
        self._token_generated = False

        # Parse command line using JupyterApp... 
        # Shouldn't need this after jupyter_server 
        # moves forward.
        JupyterApp.initialize(self, argv=argv)
        self.init_logging()
        if self._dispatching:
            return
        self.init_configurables()
        self.init_components()

        # Specific to HubShare
        self.init_db()
        self.init_hub_auth()
        self.init_extra_settings()

        # Init webapp.
        self.init_webapp()
        self.init_hubshare_handlers()


main = HubShare.launch_instance

if __name__ == '__main__':
    main()
