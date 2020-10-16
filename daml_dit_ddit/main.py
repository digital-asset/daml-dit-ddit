import argparse

import logging

from .log import setup_default_logging, LOG

from .common import die

from .subcommand_build import setup as setup_subcommand_build
from .subcommand_ditversion import setup as setup_subcommand_ditversion
from .subcommand_genargs import setup as setup_subcommand_genargs
from .subcommand_inspect import setup as setup_subcommand_inspect
from .subcommand_release import setup as setup_subcommand_release
from .subcommand_show import setup as setup_subcommand_show
from .subcommand_targetname import setup as setup_subcommand_targetname


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', help='Turn on additional logging.',
                        dest='verbose', action='store_true', default=False)

    subcommands={}
    subparsers=parser.add_subparsers(dest='subcommand_name', help='subcommand')

    def install_subcommand(name: str, help: str, setup_fn):
        cmd_fn = setup_fn(subparsers.add_parser(name, help=help))

        subcommands[name] = cmd_fn

    install_subcommand('build', 'Build a DIT file.',
                       setup_subcommand_build)

    install_subcommand('ditversion', 'Print the current version in dabl-meta.yaml',
                       setup_subcommand_ditversion)

    install_subcommand('genargs', 'Write a template integration argfile to stdout',
                       setup_subcommand_genargs)

    install_subcommand('inspect', 'Inspect the contents of a DIT file.',
                       setup_subcommand_inspect)

    install_subcommand('release', 'Tag and release the current DIT file.',
                       setup_subcommand_release)

    install_subcommand('show', 'Verify and print the current metadata file.',
                       setup_subcommand_show)

    install_subcommand('targetname', 'Print the build target filename to stdout',
                       setup_subcommand_targetname)

    kwargs = vars(parser.parse_args())

    subcommand_name = kwargs.pop('subcommand_name')
    verbose = kwargs.pop('verbose')

    setup_default_logging(level=logging.DEBUG if verbose else logging.INFO)

    cmd_fn = subcommands.get(subcommand_name)

    if cmd_fn:
        cmd_fn(**kwargs)
    else:
        parser.print_help()

        die(f'Unknown subcommand: {subcommand_name}'
            if subcommand_name else 'Subcommand missing.')

