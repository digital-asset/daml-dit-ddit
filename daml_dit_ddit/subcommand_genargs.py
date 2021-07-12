import os
from daml_dit_api import IntegrationTypeInfo

from .common import \
    show_integration_types, \
    package_meta_integration_types, \
    INTEGRATION_ARG_FILE

from .log import LOG

from .common import die, get_itype

def generate_argfile(integration_type: 'IntegrationTypeInfo'):
    with open(INTEGRATION_ARG_FILE, "w") as out:
        out.write(f'# Arguments for integration type \'{integration_type.id}\'\n')
        out.write('\n')
        out.write('"metadata":\n')
        for field in integration_type.fields:
            out.write(f'    "{field.id.strip()}": "{field.field_type.strip()}"\n')


def subcommand_main(integration_type_id: str, force: bool = False):

    if os.path.isfile(INTEGRATION_ARG_FILE):
        if force:
            LOG.info(f'Forcibly overwriting existing integration argument file: {INTEGRATION_ARG_FILE}')
            os.remove(INTEGRATION_ARG_FILE)
        else:
            die(f'Integration argument file already exists: {INTEGRATION_ARG_FILE}')

    generate_argfile(get_itype(integration_type_id))

    LOG.info(f'Integration argument file created, please update with configuration'
             f' values: {INTEGRATION_ARG_FILE}')


def setup(sp):
    sp.add_argument('integration_type_id', metavar='integration_type_id')

    sp.add_argument('--force', help='Forcibly overwrite argument file if it already exists.',
                    dest='force', action='store_true', default=False)

    return subcommand_main
