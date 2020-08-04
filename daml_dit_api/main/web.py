from typing import Any, Dict, Optional

from asyncio import ensure_future
from dataclasses import asdict, dataclass

from aiohttp import web
from aiohttp.web import Application, AppRunner, TCPSite, RouteTableDef, \
    Request, Response
from aiohttp.helpers import sentinel
from aiohttp.typedefs import LooseHeaders
from dazl.protocols.v0.json_ser_command import LedgerJSONEncoder


from .log import LOG
from .config import Configuration
from .integration_context import IntegrationContext

# cap aiohttp to allow a maximum of 100 MB for the size of a body.
CLIENT_MAX_SIZE = 100 * (1024 ** 2)

DEFAULT_ENCODER = LedgerJSONEncoder()


def json_response(
        data: Any = sentinel, *,
        text: str = None,
        body: bytes = None,
        status: int = 200,
        reason: 'Optional[str]' = None,
        headers: 'LooseHeaders' = None) -> 'web.Response':
    return web.json_response(
        data=data, text=text, body=body, status=status, reason=reason, headers=headers,
        dumps=lambda obj: DEFAULT_ENCODER.encode(obj) + '\n')


def unauthorized_response(code: str, description: str) -> 'web.HTTPUnauthorized':
    body = DEFAULT_ENCODER.encode({'code': code, 'description': description}) + '\n'
    return web.HTTPUnauthorized(text=body, content_type='application/json')


def forbidden_response(code: str, description: str) -> 'web.HTTPForbidden':
    body = DEFAULT_ENCODER.encode({'code': code, 'description': description}) + '\n'
    return web.HTTPForbidden(text=body, content_type='application/json')


def not_found_response(code: str, description: str) -> 'web.HTTPNotFound':
    body = DEFAULT_ENCODER.encode({'code': code, 'description': description}) + '\n'
    return web.HTTPNotFound(text=body, content_type='application/json')


def bad_request(code: str, description: str) -> 'web.HTTPBadRequest':
    body = DEFAULT_ENCODER.encode({'code': code, 'description': description}) + '\n'
    return web.HTTPBadRequest(text=body, content_type='application/json')


def internal_server_error(code: str, description: str) -> 'web.HTTPInternalServerError':
    body = DEFAULT_ENCODER.encode({'code': code, 'description': description}) + '\n'
    return web.HTTPInternalServerError(text=body, content_type='application/json')


def _build_healthcheck_route(
        integration_context: 'IntegrationContext') -> 'RouteTableDef':
    routes = RouteTableDef()

    @routes.get('/healthz')
    async def get_container_health(request: 'Request') -> 'Response':
        response_dict = {
            '_self': str(request.url),
            'integration': asdict(integration_context.get_status())
        }
        return json_response(response_dict)

    return routes


async def start_web_endpoint(
        config: 'Configuration',
        integration_context: 'IntegrationContext'):

    # prepare the web application
    app = Application(client_max_size=CLIENT_MAX_SIZE)

    app.add_routes(_build_healthcheck_route(integration_context))

    if integration_context.running and integration_context.webhook_context:
        app.add_routes(integration_context.webhook_context.route_table)

    LOG.info('Opening a TCP socket...')
    runner = AppRunner(app, access_log_format='%a %t "%r" %s %b')
    await runner.setup()
    site = TCPSite(runner, '0.0.0.0', config.health_port)

    LOG.info('Started the web server on port %s.', config.health_port)
    return ensure_future(site.start())
