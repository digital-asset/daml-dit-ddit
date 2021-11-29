import os
import subprocess
from dataclasses import replace

from typing import Optional

from .common import \
    die, \
    get_itype, \
    load_dabl_meta, \
    package_meta_yaml, \
    INTEGRATION_ARG_FILE, \
    VIRTUAL_ENV_DIR

from .subcommand_build import build_dar
from .subcommand_install import subcommand_main as subcommand_install
from .subcommand_genargs import subcommand_main as subcommand_genargs

from .log import LOG


RUNTIME_DIT_META_NAME = '.ddit-dit-meta.yaml'

def subcommand_main(
        integration_type_id: str,
        log_level: 'Optional[str]',
        party: 'str',
        if_version: 'Optional[str]',
        if_file: 'Optional[str]',
        args_file: 'str',
        ledger_url: 'Optional[str]',
        rebuild_dar: bool):

    # Ensure that the integration type is known, and print a useful error
    # message if not.
    get_itype(integration_type_id)


    dabl_meta = load_dabl_meta()

    dar_build_result = build_dar(dabl_meta, rebuild_dar)

    if dar_build_result:
        (dar_filename, daml_model_info) = dar_build_result

        dabl_meta = replace(
            dabl_meta,
            daml_model=daml_model_info)

    with open(RUNTIME_DIT_META_NAME, 'w') as runtime_meta_file:
        runtime_meta_file.write(package_meta_yaml(dabl_meta))

    if os.path.isfile(args_file):
        LOG.info(f'Argument file found: {args_file}')
    else:
        LOG.info(f'Argument file not found: {args_file}')
        subcommand_genargs(integration_type_id, args_file)
        die('Cannot run integration with un-edited argument file.')

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

    url_dict = { 'DABL_LEDGER_URL': ledger_url } if ledger_url else {}
    env = {
        **os.environ,
        **url_dict,
        'PYTHONPATH': 'src',
        'DABL_INTEGRATION_TYPE_ID': integration_type_id,
        'DABL_INTEGRATION_METADATA_PATH': args_file,
        'DAML_DIT_META_PATH': RUNTIME_DIT_META_NAME,
        'DAML_LEDGER_PARTY': party
    }

    if log_level:
        env['DABL_LOG_LEVEL'] = log_level

    subprocess.run([f'{VIRTUAL_ENV_DIR}/bin/python3', '-m', 'daml_dit_if.main'], env=env)


def setup(sp):
    sp.add_argument('integration_type_id', metavar='integration_type_id')

    sp.add_argument('--party', help='Specify the run as party for the integration.',
                    dest='party', action='store', default=None, required=True)

    sp.add_argument('--log-level', help='Set integration log level',
                    dest='log_level', action='store', default=None)

    sp.add_argument('--rebuild-dar', help='Rebuild and overwrite the DAR if it already exists',
                    dest='rebuild_dar', action='store_true', default=False)

    sp.add_argument('--if-version', help='Ensure the integration is run with a specific daml-dit-if, by version.',
                    dest='if_version', action='store', default=None)

    sp.add_argument('--if-file', help='Ensure the integration is run with a specific daml-dit-if, by file.',
                    dest='if_file', action='store', default=None)

    sp.add_argument('--args-file', help=f'Use a specified arguments file, defaults to {INTEGRATION_ARG_FILE}.',
                    dest='args_file', action='store', default=INTEGRATION_ARG_FILE)

    sp.add_argument('--ledger-url', help='The URL of the ledger to connect to.',
                    dest='ledger_url', action='store', default=None)

    return subcommand_main
