"""handlers for human-facing pages"""

from tornado import gen, web

from jupyterhub.handlers import BaseHandler as JupyterHubBaseHandler
from jupyterhub.services.auth import HubAuthenticated
from jupyterhub.utils import url_path_join

class BaseHandler(HubAuthenticated, JupyterHubBaseHandler):
    """A hubshare base handler"""

    # register URL patterns
    urls = []

    # The next two methods exist to circumvent the basehandler's async 
    # versions of the methods.
    def prepare(self):
        """"""
        try:
            self.get_current_user()
        except Exception:
            self.log.exception("Failed to get current user")
            self._hub_auth_user_cache = None

    @property
    def current_user(self):
        """Override .current_user accessor from tornado."""
        if not hasattr(self, '_hub_auth_user_cache'):
            raise RuntimeError("No user found.")
        return self._hub_auth_user_cache

    @property
    def hub_auth(self):
        return self.settings.get('hub_auth')

    @property
    def contents(self):
        return self.settings.get('contents_manager')

    @property
    def csp_report_uri(self):
        return self.settings.get('csp_report_uri',
            url_path_join(self.settings.get('hub_base_url', '/hub'), 'security/csp-report')
        )

    @property
    def template_namespace(self):
        user = self.get_current_user()
        return dict(
            prefix=self.base_url,
            user=user,
            login_url=self.settings['login_url'],
            logout_url=self.settings['logout_url'],
            static_url=self.static_url,
            version_hash=self.version_hash,
        )

    def finish(self):
        return super(JupyterHubBaseHandler, self).finish()


class Template404(BaseHandler):
    """Render hubshare's 404 template"""
    urls = ['.*']

    def prepare(self):
        raise web.HTTPError(404)


class RootHandler(BaseHandler):
    """Handler for serving hubshare's human facing pages"""
    urls = ['/']

    @web.authenticated
    def get(self):
        template = self.render_template('index.html')
        self.write(template)


# The exported handlers
default_handlers = [
    RootHandler,
]
