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

from daml_dit_api import IntegrationRuntimeSpec

from .config import Configuration, get_default_config

from .log import LOG, setup_default_logging

from .web import start_web_endpoint

from .integration_context import IntegrationContext

import pkg_resources


def main():
    import logging

    setup_default_logging(level=logging.DEBUG)

    # Parsing certain DAML-LF modules causes very deep stacks; increase the standxrd limit
    # to be able to handle those.
    sys.setrecursionlimit(10000)

    loop = get_event_loop()
    loop.run_until_complete(_aio_main(get_default_config()))


def create_network(url: str) -> 'Network':
    network = Network()
    network.set_config(url=url)
    return network


def load_integration_spec(config: 'Configuration') -> 'IntegrationRuntimeSpec':
    metadata_path = Path(config.integration_metadata_path)

    if metadata_path.exists():
        LOG.info('Loading integration metadata from: %r', metadata_path)

        return from_dict(
            data_class=IntegrationRuntimeSpec,
            data=yaml.safe_load(metadata_path.read_bytes()))
    else:
        raise Exception('No metadata file found at: ' + repr(metadata_path))


async def _aio_main(config: 'Configuration'):
    LOG.info('Initializing dabl-integration...')

    network = create_network(config.ledger_url)
    dazl_coro = ensure_future(run_dazl_networks(network))

    integration_spec = load_integration_spec(config)

    integration_context = IntegrationContext(config, network, integration_spec)

    await integration_context.safe_load_and_start()

    web_coro = start_web_endpoint(config, integration_context)

    integration_coro = integration_context.get_coro()

    LOG.info('dabl-integration is now ready.')

    await gather(web_coro, dazl_coro, integration_coro)


async def run_dazl_networks(*networks: 'Network'):
    """
    Run the dazl networks, and make sure that fatal dazl errors terminate the application.
    """
    LOG.info('Starting dazl network(s)...')
    # noinspection PyBroadException
    try:
        futures = [ensure_future(n.aio_run()) for n in networks]
        await gather(*futures)
    except:  # noqa
        LOG.exception('The main dazl coroutine died with an exception')
        sys.exit(9)
