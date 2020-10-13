import asyncio
import base64
import logging
import sys
import yaml

from dataclasses import dataclass
from pathlib import Path
from asyncio import ensure_future, gather, get_event_loop
from typing import Optional, Dict
from dacite import from_dict

from aiohttp import ClientSession
from yarl import URL

from aiohttp.web import Application, AppRunner, TCPSite, RouteTableDef, \
    Request, Response

from dazl import Network

from daml_dit_api import \
    IntegrationRuntimeSpec, \
    IntegrationTypeInfo

from .config import Configuration, get_default_config

from .log import LOG, setup_default_logging

from .web import start_web_endpoint

from .integration_context import IntegrationContext
from .package_metadata_introspection import get_integration_types

import pkg_resources


def FAIL(message: str):
    LOG.error(f'Fatal error: {message}')
    sys.exit(9)


def load_integration_spec(config: 'Configuration') -> 'Optional[IntegrationRuntimeSpec]':
    metadata_path = Path(config.integration_metadata_path)

    if metadata_path.exists():
        LOG.info('Loading integration metadata from: %r', metadata_path)

        yaml_metadata=yaml.safe_load(metadata_path.read_bytes())

        LOG.info('Integration metadata: %r', yaml_metadata)

        return from_dict(
            data_class=IntegrationRuntimeSpec,
            data=yaml_metadata)

    else:
        LOG.error(f'No metadata file found at: {repr(metadata_path)}')
        return None


def create_network(url: str) -> 'Network':
    network = Network()
    network.set_config(url=url)
    return network


async def run_dazl_network(network: 'Network'):
    """
    Run the dazl network, and make sure that fatal dazl errors terminate the application.
    """
    LOG.info('Starting dazl network...')

    # noinspection PyBroadException
    try:
        await network.aio_run()
    except:  # noqa
        FAIL('The main dazl coroutine died with an exception')


async def _aio_main(
        integration_type: 'IntegrationTypeInfo',
        config: 'Configuration',
        type_id: str,
        integration_spec: 'IntegrationRuntimeSpec'):

    network = create_network(config.ledger_url)
    dazl_coro = ensure_future(run_dazl_network(network))

    integration_context = \
        IntegrationContext(network, integration_type, type_id, integration_spec)

    await integration_context.safe_load_and_start()

    web_coro = start_web_endpoint(config, integration_context)

    integration_coro = integration_context.get_coro()

    LOG.info('dabl-integration is now ready.')

    await gather(web_coro, dazl_coro, integration_coro)


def main():
    setup_default_logging(level=logging.DEBUG)

    LOG.info('Initializing dabl-integration...')

    # Parsing certain DAML-LF modules causes very deep stacks;
    # increase the standard limit to be able to handle those.
    sys.setrecursionlimit(10000)

    integration_types = get_integration_types()
    config = get_default_config()
    integration_spec = load_integration_spec(config)

    type_id = config.type_id

    if integration_spec and not type_id:
        # Allow fallback to the spec file on disk, to support
        # execution on DABL clusters that do not inject type ID
        # via an environment variable.
        type_id = integration_spec.type_id

    if not type_id:
        # Guide the user to provide the type ID via the current
        # environment variable rather than with the deprecated config
        # file approach.
        raise Exception('DABL_INTEGRATION_TYPE_ID environment variable undefined')

    integration_type = integration_types.get(type_id)

    if not integration_type:
        FAIL(f'No integration of type {type_id}')

    if integration_spec:
        LOG.info('Running integration type: %r...', type_id)

        loop = get_event_loop()
        loop.run_until_complete(_aio_main(integration_type, config, type_id, integration_spec))

    else:
        FAIL('No metadata file. Terminating without running')
