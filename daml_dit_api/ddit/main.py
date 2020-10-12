import argparse

import logging

from ..main.log import \
    setup_default_logging, LOG

from .subcommand_build import \
    subcommand_main as subcommand_build, \
    setup_argparse as setup_argparse_build

from .subcommand_genargs import \
    subcommand_main as subcommand_genargs, \
    setup_argparse as setup_argparse_genargs

from .subcommand_show import \
    subcommand_main as subcommand_show, \
    setup_argparse as setup_argparse_show

def main():

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument('--verbose', dest='verbose', action='store_true', default=False)

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='subcommand_name')
    setup_argparse_build(subparsers.add_parser('build', parents=[parent]))
    setup_argparse_genargs(subparsers.add_parser('genargs', parents=[parent]))
    setup_argparse_show(subparsers.add_parser('show', parents=[parent]))

    kwargs = vars(parser.parse_args())
    subcommand_name = kwargs.pop('subcommand_name')

    verbose = kwargs.pop('verbose')

    setup_default_logging(level=logging.DEBUG if verbose else logging.INFO)

    globals()[f'subcommand_{subcommand_name}'](**kwargs)
