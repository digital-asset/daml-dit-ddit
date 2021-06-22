import os
import subprocess
import shutil

from typing import Optional

from .common import \
    die, \
    VIRTUAL_ENV_DIR, \
    load_dabl_meta, \
    package_dit_filename

from .log import LOG

def subcommand_main():

    if os.path.isdir(VIRTUAL_ENV_DIR):
        shutil.rmtree(VIRTUAL_ENV_DIR)

    target_file = package_dit_filename(load_dabl_meta())

    if os.path.isfile(target_file):
        os.remove(target_file)


def setup(sp):
    return subcommand_main
