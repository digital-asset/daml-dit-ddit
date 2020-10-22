import os

from .common import \
    load_dabl_meta, \
    package_dit_basename, \
    package_dit_filename


def subcommand_main(basename: bool):
    if basename:
        print(package_dit_basename(load_dabl_meta()))
    else:
        print(package_dit_filename(load_dabl_meta()))


def setup(sp):
    sp.add_argument('--basename', help='Return the base name only, without filename extension.',
                    dest='basename', action='store_true', default=False)
    return subcommand_main

