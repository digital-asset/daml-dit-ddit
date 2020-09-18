import asyncio
import sys
import yaml

from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from importlib import import_module
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type
from zipfile import ZipFile

from dazl import AIOPartyClient, Network, Command
from dazl.util.prim_types import to_boolean

from dacite import from_dict, Config

from daml_dit_api import \
    DABL_META_NAME, \
    IntegrationEntryPoint, \
    IntegrationEnvironment, \
    IntegrationEvents, \
    IntegrationRuntimeSpec, \
    IntegrationTimeEvents, \
    IntegrationTypeInfo, \
    IntegrationWebhookRoutes, \
    METADATA_INTEGRATION_ENABLED, \
    METADATA_COMMON_RUN_AS_PARTY, \
    METADATA_INTEGRATION_RUN_AS_PARTY, \
    METADATA_INTEGRATION_TYPE_ID, \
    PackageMetadata

from .integration_time_context import \
    IntegrationTimeContext, IntegrationTimeStatus

from .integration_webhook_context import \
    IntegrationWebhookContext, IntegrationWebhookStatus

from .integration_ledger_context import \
    IntegrationLedgerContext, IntegrationLedgerStatus

from .common import \
    InvocationStatus, \
    without_return_value, \
    with_marshalling, \
    as_handler_invocation

from .config import Configuration

from .log import LOG


@dataclass(frozen=True)
class IntegrationStatus:
    running: bool
    start_time: datetime
    error_message: 'Optional[str]'
    error_time: 'Optional[datetime]'
    webhooks: 'Optional[IntegrationWebhookStatus]'
    ledger: 'Optional[IntegrationLedgerStatus]'
    timers: 'Optional[IntegrationTimeStatus]'



def normalize_metadata_field(field_value, field_type_info):
    LOG.debug('Normalizing %r with field_type_info: %r',
              field_value, field_type_info)

    return field_value.strip()


def normalize_metadata(metadata, integration_type):
    LOG.debug('Normalizing metadata %r for integration type: %r',
              metadata, integration_type)

    field_types = {field.id: field for field in integration_type.fields}

    return {field_id: normalize_metadata_field(field_value, field_types.get(field_id))
            for (field_id, field_value)
            in metadata.items()}


def _as_int(value: Any) -> int:
    return int(value)


def get_local_dabl_meta() -> 'Optional[str]':
    filename = f'pkg/{DABL_META_NAME}'

    LOG.info('Attmpting to load DABL metadata from local file: %r', filename)

    try:
        with open(filename, "r") as f:
            return f.read()
    except:  # noqa
        LOG.exception(f'Failed to local dabl meta {filename}')
        return None


def get_pex_dabl_meta() -> 'Optional[str]':
    pex_filename = sys.argv[0]

    LOG.info('Attmpting to load DABL metadata from PEX file: %r', pex_filename)

    try:
        with ZipFile(pex_filename) as zf:
            with zf.open(DABL_META_NAME) as meta_file:
                return meta_file.read().decode('UTF-8')
    except:  # noqa
        LOG.exception(f'Failed to read {DABL_META_NAME} from PEX file {pex_filename}'
                      f' (This is an expected error in local development scenarios.)')
        return None


def get_dabl_meta() -> str:
    meta = get_pex_dabl_meta() or get_local_dabl_meta()

    if meta:
        return meta

    raise Exception(f'Could not find {DABL_META_NAME}')


def parse_qualified_symbol(symbol_text: str):

    try:
        (module_name, sym_name) = symbol_text.split(':')
    except ValueError:
        raise Exception(f'Malformed symbol {symbol_text} (Must be [module_name:symbol_name])')

    module = None

    try:
        LOG.info(f'Searching for module {module_name} in qualified symbol {symbol_text}')
        module = import_module(module_name)
    except:  # noqa
        LOG.exception(f'Failure importing integration package: {module_name}')

    if module is None:
        raise Exception(f'Unknown module {module_name} in {symbol_text}')

    return (module, sym_name)


class IntegrationContext:

    def __init__(self,
                 config: 'Configuration',
                 network: 'Network',
                 integration_spec: 'IntegrationRuntimeSpec'):

        # Allow fallback to the spec file on disk, to support
        # execution on DABL clusters that do not inject integration ID
        # via an environment variable.
        iid = config.integration_id or integration_spec.integration_id

        self.start_time = datetime.utcnow()

        self.config = config
        self.network = network
        self.integration_spec = integration_spec
        self.dabl_meta = get_dabl_meta()

        self.running = False
        self.error_message = None  # type: Optional[str]
        self.error_time = None  # type: Optional[datetime]

        self.time_context = None  # type: Optional[IntegrationTimeContext]
        self.webhook_context = None  # type: Optional[IntegrationWebhookContext]
        self.ledger_context = None  # type: Optional[IntegrationLedgerContext]
        self.int_toplevel_coro = None

    def get_integration_entrypoint(
            self,
            integration_type: 'IntegrationTypeInfo') -> 'IntegrationEntryPoint':

        (module, entry_fn_name) = parse_qualified_symbol(integration_type.entrypoint)

        return getattr(module, entry_fn_name)

    def get_integration_env_class(
            self,
            integration_type: 'IntegrationTypeInfo') -> 'Type[IntegrationEnvironment]':

        if integration_type.env_class:
            (module, env_class_name) = parse_qualified_symbol(integration_type.env_class)

            return getattr(module, env_class_name)
        else:
            return IntegrationEnvironment

    def _get_integration_types(self):
        package_meta = from_dict(
            data_class=PackageMetadata, data=yaml.safe_load(self.dabl_meta))

        package_itypes = (package_meta.integration_types
                          or package_meta.integrations  # support for deprecated
                          or [])

        return {itype.id: itype for itype in package_itypes}

    async def _load_and_start(self):
        metadata = self.integration_spec.metadata
        LOG.info('=== REGISTERING INTEGRATION: %r', self.integration_spec)

        run_as_party = metadata.get(METADATA_COMMON_RUN_AS_PARTY)

        if run_as_party is None:
            LOG.info("Falling back to old-style integration 'run as' party.")
            run_as_party = metadata.get(METADATA_INTEGRATION_RUN_AS_PARTY)

        if run_as_party is None:
            raise Exception("No 'run as' party specified for integration.")

        client = self.network.aio_party(run_as_party)

        if run_as_party is None:
            raise Exception("No 'run as' party specified for integration.")

        client = self.network.aio_party(run_as_party)

        integration_types = self._get_integration_types()

        # Allow fallback to the spec file on disk, to support
        # execution on DABL clusters that do not inject type ID
        # via an environment variable.
        type_id = self.config.type_id or self.integration_spec.type_id

        integration_type = integration_types[type_id]

        env_class = self.get_integration_env_class(integration_type)
        entry_fn = self.get_integration_entrypoint(integration_type)

        metadata = normalize_metadata(metadata, integration_type)

        LOG.info("Starting integration with metadata: %r", metadata)

        integration_env_data = {
            **metadata,
            'party': run_as_party
            }

        integration_env = from_dict(
            data_class=env_class,
            data=integration_env_data,
            config=Config(type_hooks={
                bool: to_boolean,
                int: _as_int
            })
        )

        self.time_context = IntegrationTimeContext(client)
        self.ledger_context = IntegrationLedgerContext(client)
        self.webhook_context = IntegrationWebhookContext(client)

        events = IntegrationEvents(
            time=self.time_context,
            ledger=self.ledger_context,
            webhook=self.webhook_context)

        user_coro = entry_fn(integration_env, events)

        LOG.info("Waiting for ledger client to become ready")
        await client.ready()

        await self.ledger_context.process_sweeps()

        self.running = True
        LOG.info("Integration ready")

        int_coros = [
            self.time_context.start(),
            self.ledger_context.start()
        ]

        if user_coro:
            int_coros.append(user_coro)

        self.int_toplevel_coro = asyncio.gather(*int_coros)

    def get_status(self) -> 'IntegrationStatus':
        return IntegrationStatus(
            running=self.running,
            start_time=self.start_time,
            error_message=self.error_message,
            error_time=self.error_time,
            webhooks=self.webhook_context.get_status() if self.webhook_context else None,
            ledger=self.ledger_context.get_status() if self.ledger_context else None,
            timers=self.time_context.get_status() if self.time_context else None)

    async def safe_load_and_start(self):
        try:
            await self._load_and_start()
        except:  # noqa
            ex = sys.exc_info()[1]

            self.error_message = f'{repr(ex)} - {str(ex)}'
            self.error_time = datetime.utcnow()

            LOG.exception("Failure starting integration.")

    def get_coro(self):
        return self.int_toplevel_coro
