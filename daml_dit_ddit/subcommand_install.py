import os
import subprocess
import venv

from typing import Optional

from .common import \
    die, \
    PYTHON_REQUIREMENT_FILE, \
    VIRTUAL_ENV_DIR

from .log import LOG


def install(cmd_suffix):
    install_cmd = [ f'{VIRTUAL_ENV_DIR}/bin/pip3', 'install' ]

    returncode = subprocess.run([*install_cmd, *cmd_suffix]).returncode

    if returncode != 0:
        die(f'Error installing {cmd_suffix}')


def subcommand_main(force: bool, if_version: 'Optional[str]' = None, if_file: 'Optional[str]' = None):

    if os.path.isdir(VIRTUAL_ENV_DIR):
        if force:
            LOG.info(f'Forcibly overwriting virtual environment: {VIRTUAL_ENV_DIR}')
        else:
            die(f'Virtual environment already exists: {VIRTUAL_ENV_DIR}')
    else:
        LOG.info(f'Installing into virtual environment: {VIRTUAL_ENV_DIR}')

    venv.EnvBuilder(with_pip=True, clear=force).create(VIRTUAL_ENV_DIR)

    if if_version and if_file:
        die('Cannot specify both --if-version and --if-file')

    elif if_version:
        LOG.info('Installing specific version of daml-dit-if from PyPi: %r', if_version)
        install([f'daml_dit_if=={if_version}'])

    elif if_file:
        LOG.info('Installing daml-dit-if from %r', if_file)
        install([f'{if_file}'])

    else:
        LOG.info('Installing latest daml-dit-if from PyPi')
        install(['daml_dit_if'])

    if os.path.isfile(PYTHON_REQUIREMENT_FILE):
        install(['-r', 'requirements.txt'])


def setup(sp):

    sp.add_argument('--force', help='Forcibly overwrite the virtual environment if it exists.',
                    dest='force', action='store_true', default=False)

    sp.add_argument('--if-version', help='Use a specific version of daml-dit-if.',
                    dest='if_version', action='store', default=None)

    sp.add_argument('--if-file', help='Use a specific file source for daml-dit-if.',
                    dest='if_file', action='store', default=None)

    return subcommand_main
