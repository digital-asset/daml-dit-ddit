import sys
import yaml

from dacite import from_dict

from dataclasses import asdict

from daml_dit_api import \
    DABL_META_NAME, \
    PackageMetadata

from .log import LOG


def accept_dabl_meta(data: bytes) -> 'PackageMetadata':
    return from_dict(
        data_class=PackageMetadata,
        data=yaml.safe_load(data))


def load_dabl_meta() -> 'PackageMetadata':
    with open(DABL_META_NAME, "r") as f:
        return accept_dabl_meta(f.read())


def package_meta_integration_types(
        package_metadata: 'PackageMetadata') -> 'Dict[str, IntegrationTypeInfo]':

    package_itypes = (package_metadata.integration_types
                      or package_metadata.integrations  # support for deprecated
                      or [])

    return {itype.id: itype for itype in package_itypes}


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


def die(message: str):
    LOG.error(f'Fatal Error: {message}')
    sys.exit(9)
