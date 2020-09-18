import os
from dataclasses import dataclass, asdict
from typing import Optional

from .log import LOG


@dataclass(frozen=True)
class Configuration:
    health_port: int
    ledger_url: str
    ledger_id: str
    integration_metadata_path: str
    integration_id: 'Optional[str]'
    type_id: 'Optional[str]'


def env(var: str, default: 'Optional[str]' = None) -> str:
    val = os.getenv(var)

    LOG.debug('Configuration environment lookup: %r => %r (default: %r)', var, val, default)

    if val:
        return val
    elif default:
        return default
    else:
        raise Exception(f'Missing required environment variable: {var}')


def envint(var: str, default: 'Optional[int]' = None) -> int:
    val = env(var, str(default) if default else None)

    try:
        return int(val)
    except ValueError:
        raise Exception(f'Invalid integer {val} in environment variable: {var}')


def get_default_config() -> 'Configuration':
    config = Configuration(
        health_port=envint('DABL_HEALTH_PORT', 8089),
        ledger_url=env('DABL_LEDGER_URL', 'http://localhost:6865'),
        ledger_id=env('DABL_LEDGER_ID', 'cloudbox'),
        integration_metadata_path=env('DABL_INTEGRATION_METADATA_PATH', 'int_args.yaml'),
        integration_id=os.getenv('DABL_INTEGRATION_INTEGRATION_ID'),
        type_id=os.getenv('DABL_INTEGRATION_TYPE_ID'))

    LOG.info('Configuration: %r', asdict(config))

    return config
