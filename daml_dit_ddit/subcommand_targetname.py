import os

from .common import \
    load_dabl_meta, \
    package_dit_filename


def subcommand_main():
    print(package_dit_filename(load_dabl_meta()))


def setup(sp):
    return subcommand_main

