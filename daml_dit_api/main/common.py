import sys
import collections

from dataclasses import dataclass
from functools import wraps
from typing import Optional

from dazl import AIOPartyClient

from daml_dit_api import IntegrationResponse

from .log import LOG


@dataclass
class InvocationStatus:
    index: int
    command_count: int
    use_count: int
    error_count: int
    error_message: 'Optional[str]'


def without_return_value(fn):

    @wraps(fn)
    async def wrapped(*args, **kwargs):
        await fn(*args, **kwargs)

    return wrapped


def with_marshalling(mfn, fn):

    @wraps(fn)
    async def wrapped(arg):
        await fn(mfn(arg))

    return wrapped


def normalize_integration_response(response):
    LOG.info('Normalizing integration response: %r', response)

    if isinstance(response, IntegrationResponse):
        LOG.info('Integration Response passthrough')
        return response

    commands = []
    if isinstance(response, collections.Sequence):
        commands = response
    elif response:
        commands = [response]
    else:
        commands = []

    LOG.info('Integration response with cmds: %r', commands)

    return IntegrationResponse(commands=commands)


def as_handler_invocation(client: 'AIOPartyClient', inv_status: 'InvocationStatus', fn):
    @wraps(fn)
    async def wrapped(*args, **kwargs):
        LOG.info('Invoking for invocation status: %r', inv_status)
        inv_status.use_count += 1

        response = None
        try:
            response = normalize_integration_response(
                await fn(*args, **kwargs))

            if response.commands:
                LOG.debug('Submitting ledger commands: %r', response.commands)

                inv_status.command_count += len(response.commands)
                await client.submit(response.commands)

            return response

        except Exception:
            inv_status.error_count += 1
            inv_status.error_message = repr(sys.exc_info()[1])
            LOG.exception('Error while processing: ' + inv_status)

    return wrapped
