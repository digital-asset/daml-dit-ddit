import os

from .log import LOG

from .common import \
    load_dabl_meta, \
    die


def subcommand_main():
    dabl_meta = load_dabl_meta()

    base_filename = f'{dabl_meta.catalog.name}-{dabl_meta.catalog.version}'

    dit_filename = f'{base_filename}.dit'

    print(dit_filename)


def setup(sp):
    return subcommand_main

