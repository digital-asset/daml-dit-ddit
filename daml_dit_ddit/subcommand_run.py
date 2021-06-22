import os
import subprocess

from typing import Optional

from .common import \
    die, \
    get_itype, \
    VIRTUAL_ENV_DIR

from .subcommand_install import subcommand_main as subcommand_install

from .log import LOG


def subcommand_main(integration_type_id: str, log_level: 'Optional[str]', party: 'Optional[str]',
                    if_version: 'Optional[str]', if_file: 'Optional[str]'):

    # Ensure that the integration type is known, and print a useful error
    # message if not.
    get_itype(integration_type_id)

    if if_file or if_version:
        # Forcibly ensure the use of a specific version of
        # daml-dit-if. These options are intended to streamline the cases
        # of iterating on daml-dit-if or testing an integration on
        # downlevel versions of the framework that might still be in
        # use in production Daml Hub.
        LOG.info(f"Ensuring specific version of daml-dit-if: {if_version or if_file}")
        subcommand_install(True, if_version, if_file)

    elif not os.path.isdir(VIRTUAL_ENV_DIR):
        LOG.info("Virtual environment missing, installing now.")
        subcommand_install(False)

    env = {
        **os.environ,
        'PYTHONPATH': 'src',
        'DABL_INTEGRATION_TYPE_ID': integration_type_id
    }

    if party:
        env['DAML_LEDGER_PARTY'] = party

    if log_level:
        env['DABL_LOG_LEVEL'] = log_level

    subprocess.run([f'{VIRTUAL_ENV_DIR}/bin/python3', '-m', 'daml_dit_if.main'], env=env)


def setup(sp):
    sp.add_argument('integration_type_id', metavar='integration_type_id')

    sp.add_argument('--party', help='Specify the run as party for the integration.',
                    dest='party', action='store', default=None)

    sp.add_argument('--log-level', help='Set integration log level',
                    dest='log_level', action='store', default=None)

    sp.add_argument('--if-version', help='Use a specific version of daml-dit-if.',
                    dest='if_version', action='store', default=None)

    sp.add_argument('--if-file', help='Ensure the integration is run with a specific daml-dit-if.',
                    dest='if_file', action='store', default=None)


    return subcommand_main
