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

from traitlets.config import Application, catch_config_error
from traitlets import (
    Bool, Dict, Integer, List, Unicode,
    default,
)

from jupyterhub.log import CoroutineLogFormatter, log_request
from jupyterhub.utils import url_path_join

from sqlalchemy.exc import OperationalError
from .orm import new_session_factory
from .contents import HubShareManager

ROOT = os.path.dirname(__file__)
STATIC_FILES_DIR = os.path.join(ROOT, 'static')
TEMPLATES_DIR = os.path.join(ROOT, 'templates')


def load_handlers(name):
    """Load the (URL pattern, handler) tuples for each component."""
    mod = __import__(name, fromlist=['default_handlers'])
    return mod.default_handlers

# Waiting for traitlets 5.0
# class UnicodeFromEnv(Unicode):
#     """A Unicode trait that gets its default value from the environment

#     Use .tag(env='VARNAME') to specify the environment variable to use.
#     """
#     def default(self, obj=None):
#         env_key = self.metadata.get('env')
#         if env_key in os.environ:
#             return os.environ[env_key]
#         else:
#             return self.default_value

def get_environ(env_key, default):
    if env_key in os.environ:
        return os.environ[env_key]
    else:
        return default


aliases = {
    'root_dir': 'HubShareManager.root_dir'
}


class HubShare(Application):
    """The HubShare application"""
    @property
    def version(self):
        import pkg_resources
        return pkg_resources.get_distribution('hubshare').version

    description = __doc__
    aliases = Dict(aliases)
    classes = List([ContentsManager])

    config_file = Unicode('hubshare_config.py',
        help="The config file to load",
    ).tag(config=True)

    generate_config = Bool(False,
        help="Generate default config file",
    ).tag(config=True)

    hub_users = List([],
        help="List of JupyterHub authenticated users."
    ).tag(config=True)

    base_url = Unicode(config=True)

    db_url = Unicode('sqlite:///jupyterhub.sqlite',
        help="url for the database. e.g. `sqlite:///jupyterhub.sqlite`"
    ).tag(config=True)

    db_kwargs = Dict(
        help="""Include any kwargs to pass to the database connection.
        See sqlalchemy.create_engine for details.
        """
    ).tag(config=True)

    upgrade_db = Bool(False,
        help="""Upgrade the database automatically on start.

        Only safe if database is regularly backed up.
        Only SQLite databases will be backed up to a local file automatically.
        """
    ).tag(config=True)
    
    reset_db = Bool(False,
        help="Purge and reset the database."
    ).tag(config=True)
    
    debug_db = Bool(False,
        help="log all database transactions. This has A LOT of output"
    ).tag(config=True)

    @default('base_url')
    def _base_url_default(self):
        return get_environ(
            'JUPYTERHUB_SERVICE_PREFIX',
            '/services/hubshare/'
        )

    hub_api_url = Unicode(config=True)

    @default('hub_api_url')
    def _hub_api_url_default(self):
        return get_environ(
            'JUPYTERHUB_API_URL',
            'http://127.0.0.1:8081/hub/api/',
        )

    hub_api_token = Unicode(config=True)

    @default('hub_api_token')
    def _hub_api_token_default(self):
        return get_environ(
            'JUPYTERHUB_API_TOKEN',
            ''
        )

    hub_base_url = Unicode(config=True)

    @default('hub_base_url')
    def _hub_base_url_default(self):
        return get_environ(
            'JUPYTERHUB_BASE_URL',
            'http://127.0.0.1:8000/'
        )

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

    template_paths = List(
        help="Paths to search for jinja templates.",
    ).tag(config=True)
    @default('template_paths')
    def _template_paths_default(self):
        return [TEMPLATES_DIR]

    contents_manager_cls = HubShareManager

    tornado_settings = Dict()

    _log_formatter_cls = CoroutineLogFormatter

    @default('log_level')
    def _log_level_default(self):
        return logging.INFO

    @default('log_datefmt')
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    @default('log_format')
    def _log_format_default(self):
        """override default log format to include time"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    def init_db(self):
        """Create the database connection"""
        self.log.debug("Connecting to db: %s", self.db_url)

        try:
            self.session_factory = new_session_factory(
                self.db_url,
                reset=self.reset_db,
                echo=self.debug_db,
                **self.db_kwargs
            )
            self.db = self.session_factory()
        except OperationalError as e:
            self.log.error("Failed to connect to db: %s", self.db_url)
            self.log.debug("Database error was:", exc_info=True)
            # if self.db_url.startswith('sqlite:///'):
            #     self._check_db_path(self.db_url.split(':///', 1)[1])
            self.log.critical('\n'.join([
                "If you recently upgraded JupyterHub, try running",
                "    jupyterhub upgrade-db",
                "to upgrade your JupyterHub database schema",
            ]))
            self.exit(1)

    def init_logging(self):
        """Initialize logging"""
        # This prevents double log messages because tornado use a root logger that
        # self.log is a child of. The logging module dipatches log messages to a log
        # and all of its ancenstors until propagate is set to False.
        self.log.propagate = False

        _formatter = self._log_formatter_cls(
            fmt=self.log_format,
            datefmt=self.log_datefmt,
        )

        # hook up tornado 3's loggers to our app handlers
        for log in (app_log, access_log, gen_log):
            # ensure all log statements identify the application they come from
            log.name = self.log.name
        logger = logging.getLogger('tornado')
        logger.propagate = True
        logger.parent = self.log
        logger.setLevel(self.log.level)

    def init_contents_manager(self):
        """Initialize the contents manager"""
        self.contents_manager = self.contents_manager_cls()

    def init_tornado_settings(self):
        """Initialize tornado config"""
        jinja_options = dict(
            autoescape=True,
        )
        jinja_env = Environment(
            loader=FileSystemLoader(self.template_paths),
            **jinja_options
        )

        # if running from git directory, disable caching of require.js
        # otherwise cache based on server start time
        parent = os.path.dirname(ROOT)
        if os.path.isdir(os.path.join(parent, '.git')):
            version_hash = ''
        else:
            version_hash=datetime.now().strftime("%Y%m%d%H%M%S"),

        settings = dict(
            log_function=log_request,
            config=self.config,
            log=self.log,
            base_url=self.base_url,
            hub_base_url = self.hub_base_url,
            logout_url=url_path_join(self.hub_base_url, 'hub/logout'),
            static_path=STATIC_FILES_DIR,
            static_url_prefix=url_path_join(self.base_url, 'static/'),
            template_path=self.template_paths,
            jinja2_env=jinja_env,
            version_hash=version_hash,
            xsrf_cookies=True,
            hub_users=self.hub_users,
            db=self.db,
            contents_manager=self.contents_manager
        )
        # allow configured settings to have priority
        settings.update(self.tornado_settings)
        self.tornado_settings = settings

    def init_handlers(self):
        """Load hubshare's tornado request handlers"""
        handlers = []
        handlers.extend(load_handlers('hubshare.handlers'))
        handlers.extend(load_handlers('hubshare.apihandlers'))
        #handlers.extend(load_handlers('hubshare.handlers'))
        self.handlers = [(url_path_join(self.base_url, url), handler)
                        for url, handler in handlers]

    def init_tornado_application(self):
        self.tornado_application = web.Application(
            self.handlers, 
            **self.tornado_settings)

    @catch_config_error
    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        if self.generate_config or self.subapp:
            return
        self.init_db()
        self.init_contents_manager()
        self.init_handlers()
        self.init_tornado_settings()
        self.init_tornado_application()

    def start(self):
        if self.subapp:
            self.subapp.start()
            return

        if self.generate_config:
            self.write_config_file()
            return

        self.http_server = HTTPServer(self.tornado_application, xheaders=True)
        self.http_server.listen(self.port, address=self.ip)

        self.log.info("Running HubShare at http://%s:%i%s", self.ip, self.port, self.base_url)
        IOLoop.current().start()

main = HubShare.launch_instance

if __name__ == '__main__':
    main()
