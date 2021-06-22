from daml_dit_api import IntegrationTypeInfo

from .common import \
    load_dabl_meta, \
    show_integration_types, \
    package_meta_integration_types

from .log import LOG

from .common import get_itype

def generate_argfile(integration_type: 'IntegrationTypeInfo'):
    print('"metadata":')

    print(f'    "runAs": "party"')
    for field in integration_type.fields:
        print(f'    "{field.id.strip()}": "{field.field_type.strip()}"')


def subcommand_main(integration_type_id):
    generate_argfile(get_itype(integration_type_id))


def setup(sp):
    sp.add_argument('integration_type_id', metavar='integration_type_id')
    return subcommand_main
