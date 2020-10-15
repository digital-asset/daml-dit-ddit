import os
import yaml

from dataclasses import asdict

from zipfile import ZipFile

from daml_dit_api import \
    DABL_META_NAME

from .common import \
    die, \
    accept_dabl_meta, \
    show_package_summary


def show_subdeployments(dabl_meta: 'PackageMetadata', files):
    subdeployments = dabl_meta.subdeployments

    if len(subdeployments) > 0:
        print('\nSubdeployments:')

        for sd in subdeployments:
            status = "MISSING" if (sd not in files) else "ok"
            print(f'   {sd} ({status})')


def subcommand_main(dit_filename: str):
    if not os.path.exists(dit_filename):
        die(f'DIT file not found: {dit_filename}')

    with ZipFile(dit_filename, 'a') as ditfile:
        filenames = set(ditfile.namelist())

        try:
            with ditfile.open(DABL_META_NAME) as meta_file:
                dabl_meta = accept_dabl_meta(meta_file.read())

                show_package_summary(dabl_meta)
                show_subdeployments(dabl_meta, filenames)

        except KeyError:
            die(f'DIT file missing metadata ({DABL_META_NAME} missing): {dit_filename}')


def setup(sp):
    sp.add_argument('dit_filename', metavar='dit_filename')
    return subcommand_main
