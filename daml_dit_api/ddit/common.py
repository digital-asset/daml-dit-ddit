import sys
import yaml

from dacite import from_dict

from daml_dit_api import \
    DABL_META_NAME, \
    PackageMetadata

from ..main.package_metadata_introspection import \
    package_meta_integration_types

from ..main.log import LOG


def load_dabl_meta() -> 'PackageMetadata':
    with open(DABL_META_NAME, "r") as f:
        return from_dict(
            data_class=PackageMetadata,
            data=yaml.safe_load(f.read()))


def show_integration_types(dabl_meta: 'PackageMetadata'):
    itypes = package_meta_integration_types(dabl_meta)

    if len(itypes) > 0:
        print('\nIntegration Types:')

        for itype in itypes.values():
            print(f'   {itype.id} - {itype.name}')


def die(message: str):
    LOG.error(f'Fatal Error: {message}')
    sys.exit(9)
