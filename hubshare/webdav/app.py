from tempfile import gettempdir

from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.default_conf import DEFAULT_CONFIG as config

import tornado.wsgi


from wsgidav.debug_filter import WsgiDavDebugFilter
from wsgidav.dir_browser import WsgiDavDirBrowser
from wsgidav.error_printer import ErrorPrinter
from wsgidav.http_authenticator import HTTPAuthenticator
from wsgidav.request_resolver import RequestResolver



# Testing with root provider
root_path = gettempdir()
provider = FilesystemProvider(root_path)

config["provider_mapping"] = {"/": provider}
config["middleware_stack"] = [
    WsgiDavDebugFilter,
    ErrorPrinter,
    HTTPAuthenticator,
    WsgiDavDirBrowser,
    RequestResolver,
]
config["http_authenticator"] = {
    # None: dc.simple_dc.SimpleDomainController(user_mapping)
    #"domain_controller": JhubDomainController,
    "accept_basic": True,  # Allow basic authentication, True or False
    "accept_digest": False,  # Allow digest authentication, True or False
}

def init_storage_app():
    app = WsgiDAVApp(config)
    return tornado.wsgi.WSGIContainer(app)
