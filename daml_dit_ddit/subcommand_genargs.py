from daml_dit_api import IntegrationTypeInfo

from .common import \
    load_dabl_meta, \
    show_integration_types, \
    package_meta_integration_types


def generate_argfile(integration_type: 'IntegrationTypeInfo'):
    print('"metadata":')

    print(f'    "runAs": "party"')
    for field in integration_type.fields:
        print(f'    "{field.id.strip()}": "{field.field_type.strip()}"')


def subcommand_main(type_id):
    dabl_meta = load_dabl_meta()

    itypes = package_meta_integration_types(dabl_meta)

    itype = itypes.get(type_id)

    if itype:
        generate_argfile(itypes[type_id])
    else:
        print(f'Unknown integration type: {type_id}\n')

        show_integration_types(dabl_meta)


def setup(sp):
    sp.add_argument('type_id', metavar='type_id')
    return subcommand_main
