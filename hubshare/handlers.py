"""handlers for human-facing pages"""

from tornado import gen, web

from jupyterhub.services.auth import HubAuthenticated
from jupyterhub.utils import url_path_join

class BaseHandler(HubAuthenticated, web.RequestHandler):
    """A hubshare base handler"""

    # register URL patterns
    urls = []

    @property
    def log_function(self):
        return self.settings['log_function']

    @property
    def config(self):
        return self.settings['config']

    @property
    def log(self):
        return self.settings['log']

    @property
    def base_url(self):
        return self.settings['base_url']

    @property
    def login_url(self):
        return self.settings['login_url']

    @property
    def hub_base_url(self):
        return self.settings['hub_base_url']

    @property
    def logout_url(self):
        return self.settings['logout_url']

    @property
    def static_path(self):
        return self.settings['static_path']

    @property
    def static_url_prefix(self):
        return self.settings['static_url_prefix']

    @property
    def template_path(self):
        return self.settings['template_path']

    @property
    def jinja2_env(self):
        return self.settings['jinja2_env']

    @property
    def version_hash(self):
        return self.settings['version_hash']

    @property
    def xsrf_cookies(self):
        return self.settings['xsrf_cookies']

    @property
    def hub_auth(self):
        return self.settings.get('hub_auth')

    @property
    def webdav_app(self):
        return self.settings['webdav_app']

    @property
    def webdav_client(self):
        return self.settings['webdav_client']    

    @property
    def csp_report_uri(self):
        return self.settings.get('csp_report_uri',
            url_path_join(self.settings.get('hub_base_url', '/hub'), 'security/csp-report')
        )

    @property
    def template_namespace(self):
        ns = dict(
            prefix=self.base_url,
            #user=user,
            login_url=self.settings['login_url'],
            logout_url=self.settings['logout_url'],
            static_url=self.static_url,
            version_hash=self.version_hash,
        )
        return ns
        
    def get_template(self, name):
        """Return the jinja template object for a given name"""
        return self.settings['jinja2_env'].get_template(name)

    def render_template(self, name, **ns):
        template_ns = {}
        template_ns.update(self.template_namespace)
        template_ns.update(ns)
        template = self.get_template(name)
        return template.render(**template_ns)

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


class WebDavHandler(web.FallbackHandler):
    
    SUPPORTED_METHODS = (
        'GET',
        'COPY',
        'LOCK',
        'MKCOL',
        'MOVE',
        'PROPFIND',
        'PROPPATCH',
        'UNLOCK',
    )


# The exported handlers
default_handlers = [
    RootHandler,
]
