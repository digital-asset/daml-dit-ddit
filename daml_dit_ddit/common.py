import sys
from typing import Dict, NoReturn
from daml_dit_api.package_metadata import CatalogInfo
import yaml

from dacite import from_dict

from dataclasses import asdict

from hashlib import sha256

from daml_dit_api import \
    DABL_META_NAME, \
    IntegrationTypeInfo, \
    PackageMetadata

from .log import LOG



def die(message: str) -> 'NoReturn':
    LOG.error(f'Fatal Error: {message}')
    sys.exit(9)


def artifact_hash(artifact_bytes: bytes) -> str:
    return sha256(artifact_bytes).hexdigest()


def accept_dabl_meta(data: bytes) -> 'PackageMetadata':
    try:
        return from_dict(
            data_class=PackageMetadata,
            data=yaml.safe_load(data))
    except:
        die(f'Error loading project metadata file: {DABL_META_NAME}')


def load_dabl_meta() -> 'PackageMetadata':
    try:
        with open(DABL_META_NAME, "r") as f:
            return accept_dabl_meta(f.read().encode())
    except FileNotFoundError:
        die(f'Project metadata file not found: {DABL_META_NAME}')


def package_meta_integration_types(
        package_metadata: 'PackageMetadata') -> 'Dict[str, IntegrationTypeInfo]':

    package_itypes = (package_metadata.integration_types
                      or package_metadata.integrations  # support for deprecated
                      or [])

    return {itype.id: itype for itype in package_itypes}

def with_catalog(dabl_meta: 'PackageMetadata') -> 'CatalogInfo':
    if dabl_meta.catalog is None:
        die(f'Missing catalog information in {DABL_META_NAME}')
    else:
        return dabl_meta.catalog

def package_dit_basename(dabl_meta: 'PackageMetadata') -> str:
    catalog = with_catalog(dabl_meta)
    return f'{catalog.name}-{catalog.version}'

def package_dit_filename(dabl_meta: 'PackageMetadata') -> str:
    basename = package_dit_basename(dabl_meta)

    return f'{basename}.dit'


def show_integration_types(dabl_meta: 'PackageMetadata'):
    itypes = package_meta_integration_types(dabl_meta)

    if len(itypes) > 0:
        print('\nIntegration Types:')

        for itype in itypes.values():
            print(f'   {itype.id} - {itype.name}')


def show_package_summary(dabl_meta: 'PackageMetadata'):
    print('Package Catalog:')
    for (k, v) in asdict(dabl_meta.catalog).items():
        print(f'   {k} : {v}')

    show_integration_types(dabl_meta)


def package_meta_yaml(dabl_meta: 'PackageMetadata'):
    return yaml.dump(
        asdict(dabl_meta),
        default_flow_style=True,
        default_style='"')

def read_binary_file(filename: str) -> bytes:
    with open(filename, mode='rb') as file:
        file_contents = file.read()

    return file_contents
