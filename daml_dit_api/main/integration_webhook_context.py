from dataclasses import dataclass
from typing import Optional, Sequence
from functools import wraps

from aiohttp import web
from aiohttp.web import RouteTableDef

from .common import \
    InvocationStatus, \
    without_return_value, \
    as_handler_invocation

from daml_dit_api import IntegrationWebhookRoutes

from .log import LOG


def empty_success_response() -> 'web.HTTPOk':
    return web.HTTPOk()


@dataclass
class WebhookRouteStatus(InvocationStatus):
    url_path: str
    method: str
    label: 'Optional[str]'


@dataclass
class IntegrationWebhookStatus:
    routes: 'Sequence[WebhookRouteStatus]'


class IntegrationWebhookContext(IntegrationWebhookRoutes):

    def __init__(self, client):
        self.route_table = RouteTableDef()
        self.client = client

        self.routes = []  # type: List[WebhookRouteStatus]

    def _with_resp_handling(self, status: 'InvocationStatus', fn):

        @wraps(fn)
        async def wrapped(request):
            hook_response = await fn(request)

            if hook_response.response is None:
                response = empty_success_response()
            else:
                response = hook_response.response

            LOG.debug('Webhook Response: %r', response)

            return response

        return wrapped

    def _notice_hook_route(self, url_path: str, method: str,
                           label: 'Optional[str]') -> 'WebhookRouteStatus':

        route_status = \
            WebhookRouteStatus(
                index=len(self.routes),
                url_path=url_path,
                method=method,
                label=label,
                command_count=0,
                use_count=0,
                error_count=0,
                error_message=None)

        self.routes.append(route_status)

        return route_status

    def _url_path(self, url_suffix: 'Optional[str]'):
        return '/integration/{integration_id}' + (url_suffix or '')

    def post(self, url_suffix: 'Optional[str]' = None, label: 'Optional[str]' = None):
        path = self._url_path(url_suffix)
        hook_status = self._notice_hook_route(path, 'post', label)

        def wrap_method(func):
            return self.route_table.post(path=path)(
                self._with_resp_handling(
                    hook_status,
                    as_handler_invocation(
                        self.client, hook_status, func)))

        return wrap_method

    def get(self, url_suffix: 'Optional[str]' = None, label: 'Optional[str]' = None):
        path = self._url_path(url_suffix)
        hook_status = self._notice_hook_route(path, 'get', label)

        def wrap_method(func):
            return self.route_table.get(path=path)(
                self._with_resp_handling(
                    hook_status,
                    as_handler_invocation(
                        self.client, hook_status, func)))

        return wrap_method

    def get_status(self) -> 'IntegrationWebhookStatus':
        return IntegrationWebhookStatus(
            routes=self.routes)
