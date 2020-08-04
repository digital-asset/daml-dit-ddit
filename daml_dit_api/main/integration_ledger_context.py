import asyncio
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Tuple

from dazl import AIOPartyClient
from dazl.model.core import ContractMatch
from dazl.model.reading import ContractCreateEvent
from dazl.model.writing import EventHandlerResponse

from daml_dit_api import \
    IntegrationLedgerEvents, \
    IntegrationLedgerContractCreateEvent, \
    IntegrationLedgerContractArchiveEvent, \
    IntegrationLedgerTransactionStartEvent, \
    IntegrationLedgerTransactionEndEvent

from .common import \
    InvocationStatus, \
    without_return_value, \
    as_handler_invocation, \
    with_marshalling

from .log import LOG


Sweep = Tuple[Any,
              Optional[ContractMatch],
              Callable[[ContractCreateEvent], EventHandlerResponse]]


PendingHandlerCall = Callable[[], None]


@dataclass
class LedgerHandlerStatus(InvocationStatus):
    description: str
    sweep_enabled: bool
    flow_enabled: bool


@dataclass
class IntegrationLedgerStatus:
    pending_calls: int
    sweep_events: int
    event_handlers: 'Sequence[LedgerHandlerStatus]'


class IntegrationLedgerContext(IntegrationLedgerEvents):
    def __init__(self, client: 'AIOPartyClient'):
        self.pending_queue = \
            asyncio.Queue()  # type: asyncio.Queue[PendingHandlerCall]

        self.client = client
        self.sweep_events = 0
        self.handlers = []  # type: List[LedgerHandlerStatus]
        self.sweeps = []  # type: List[Sweep]
        self.init_handlers = []  # type: List[PendingHandlerCall]
        self.ready_handlers = []  # type: List[PendingHandlerCall]

    def _notice_handler(
            self, description: str,
            sweep_enabled: bool, flow_enabled: bool) -> 'LedgerHandlerStatus':

        handler_status = \
            LedgerHandlerStatus(
                index=len(self.handlers),
                description=description,
                command_count=0,
                use_count=0,
                error_count=0,
                error_message=None,
                sweep_enabled=sweep_enabled,
                flow_enabled=flow_enabled)

        self.handlers.append(handler_status)

        return handler_status

    async def worker(self):
        LOG.info('Ledger context worker starting...')
        while True:
            LOG.info('...waiting for ledger event....')
            pending_call = await self.pending_queue.get()
            try:
                LOG.debug('...received ledger event: %r', pending_call)
                await pending_call()

            except:  # noqa: E722
                LOG.exception('Uncaught error in Ledger context worker loop.')

    async def process_sweeps(self):
        LOG.info("Invoking init handlers")

        for init_handler in self.init_handlers:
            await init_handler()

        for (template, match, wfunc) in self.sweeps:
            LOG.info('Processing sweep for %r', template)

            for (cid, cdata) in self.client.find_active(template, match).items():
                LOG.info('Sweep contract: %r => %r', cid, cdata)

                self.sweep_events += 1

                await wfunc(IntegrationLedgerContractCreateEvent(
                    initial=True,
                    cid=cid,
                    cdata=cdata))

        LOG.info("Sweeps processed, invoking ready handlers")

        for ready_handler in self.ready_handlers:
            await ready_handler()

        LOG.info("Done with ready handlers")

    def _with_deferral(self, handler):

        async def wrapped(*args, **kwargs):
            async def pending():
                await handler(*args, **kwargs)

            LOG.info("Deferring call: %r", pending)
            await self.pending_queue.put(pending)

        return wrapped

    def _to_int_create_event(self, dazl_event):
        return IntegrationLedgerContractCreateEvent(
            initial=False,
            cid=dazl_event.cid,
            cdata=dazl_event.cdata)

    def ledger_init(self):
        handler_status = self._notice_handler('Ledger Init', False, True)

        def wrap_method(func):
            handler = self._with_deferral(
                without_return_value(
                    as_handler_invocation(
                        self.client, handler_status, func)))

            self.init_handlers.append(handler)

            return handler

        return wrap_method

    def ledger_ready(self):
        handler_status = self._notice_handler('Ledger Ready', False, True)

        def wrap_method(func):
            handler = self._with_deferral(
                without_return_value(
                    as_handler_invocation(
                        self.client, handler_status, func)))

            self.ready_handlers.append(handler)

            return handler

        return wrap_method

    def transaction_start(self):
        handler_status = self._notice_handler('Transaction Start', False, True)

        def to_int_event(dazl_event):
            return IntegrationLedgerTransactionEndEvent(
                command_id=dazl_event.command_id,
                workflow_id=dazl_event.workflow_id,
                contract_events=[self._to_int_create_event(e)
                                 for e in dazl_event.contract_events])

        def wrap_method(func):
            handler = self._with_deferral(
                with_marshalling(
                    to_int_event,
                    without_return_value(
                        as_handler_invocation(
                            self.client, handler_status, func))))

            self.client.add_ledger_transaction_start(handler)

            return handler

        return wrap_method

    def transaction_end(self):
        handler_status = \
            self._notice_handler('Transaction End', False, True)

        def to_int_event(dazl_event):
            return IntegrationLedgerTransactionEndEvent(
                command_id=dazl_event.command_id,
                workflow_id=dazl_event.workflow_id,
                contract_events=[self._to_int_create_event(e)
                                 for e in dazl_event.contract_events])

        def wrap_method(func):
            handler = self._with_deferral(
                with_marshalling(
                    to_int_event,
                    without_return_value(
                        as_handler_invocation(
                            self.client, handler_status, func))))

            self.client.add_ledger_transaction_end(handler)

            return handler

        return wrap_method

    def contract_created(
            self, template: Any, match: 'Optional[ContractMatch]' = None,
            sweep: bool = True, flow: bool = True):

        handler_status = \
            self._notice_handler(f'Contract Create - {template}', sweep, flow)

        def wrap_method(func):
            wfunc = self._with_deferral(
                without_return_value(
                    as_handler_invocation(
                        self.client, handler_status, func)))

            if sweep:
                self.sweeps.append((template, match, wfunc))

            handler = with_marshalling(self._to_int_create_event, wfunc)

            if flow:
                self.client.add_ledger_created(template, match=match, handler=handler)

            return handler

        return wrap_method

    def contract_archived(self, template: Any, match: 'Optional[ContractMatch]' = None):

        handler_status = \
            self._notice_handler(f'Contract Archive - {template}', False, True)

        def to_int_event(dazl_event):
            return IntegrationLedgerContractArchiveEvent(
                cid=dazl_event.cid)

        def wrap_method(func):
            handler = self._with_deferral(
                with_marshalling(
                    to_int_event,
                    without_return_value(
                        as_handler_invocation(
                            self.client, handler_status, func))))

            self.client.add_ledger_archived(template, match=match, handler=handler)

            return handler

        return wrap_method

    def get_status(self) -> 'IntegrationLedgerStatus':
        return IntegrationLedgerStatus(
            pending_calls=self.pending_queue.qsize(),
            sweep_events=self.sweep_events,
            event_handlers=self.handlers)

    async def start(self):
        return asyncio.create_task(self.worker())
