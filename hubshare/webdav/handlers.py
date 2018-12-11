"""handlers for human-facing pages"""

from tornado import gen, web
from tornado.httputil import HTTPServerRequest

from jupyterhub.handlers import BaseHandler as JupyterHubBaseHandler
from jupyterhub.services.auth import HubAuthenticated
from jupyterhub.utils import url_path_join
from tornado.web import RequestHandler


class BaseHandler(HubAuthenticated, RequestHandler):
    """A hubshare base handler"""

    hub_users = ['zsailer']
    allow_admin = True
    # The next two methods exist to circumvent the basehandler's async
    # versions of the methods.
    @property
    def storage_app(self):
        return self.settings['storage_app']

    @property
    def csp_report_uri(self):
        return self.settings.get('csp_report_uri',
                                 url_path_join(self.settings.get(
                                     'hub_base_url', '/hub'), 'security/csp-report')
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
        return super(BaseHandler, self).finish()


class RootHandler(BaseHandler):

    def get(self):
        print(self.get_current_user())
        print(self.hub_auth)
        print(self.hub_auth.api_token)
        dav_request = HTTPServerRequest(
            method="GET",
            uri="/",
            connection=self.request.connection
        )
        self.storage_app(dav_request)

class PathHandler(BaseHandler):

    pass


# The exported handlers
default_handlers = [
    (r'/', RootHandler)
]
