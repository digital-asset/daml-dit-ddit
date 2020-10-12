import sys
import yaml
from dacite import from_dict, Config

from typing import Optional, Dict

from .log import LOG
from zipfile import ZipFile

from daml_dit_api import \
    DABL_META_NAME, \
    PackageMetadata, \
    IntegrationTypeInfo

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


def get_package_metadata() -> 'PackageMetadata':
    dabl_meta = get_pex_dabl_meta() or get_local_dabl_meta()

    if dabl_meta:
        return from_dict(
            data_class=PackageMetadata,
            data=yaml.safe_load(dabl_meta))

    raise Exception(f'Could not find {DABL_META_NAME}')


def package_meta_integration_types(
        package_metadata: 'PackageMetadata') -> 'Dict[str, IntegrationTypeInfo]':

    package_itypes = (package_metadata.integration_types
                      or package_metadata.integrations  # support for deprecated
                      or [])

    return {itype.id: itype for itype in package_itypes}


def get_integration_types() -> 'Dict[str, IntegrationTypeInfo]':

    return package_meta_integration_types(get_package_metadata())
