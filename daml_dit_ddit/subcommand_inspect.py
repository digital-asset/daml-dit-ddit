import os
import yaml
from hashlib import sha256

from dataclasses import asdict

from zipfile import ZipFile

from daml_dit_api import \
    DABL_META_NAME

from .common import \
    die, \
    accept_dabl_meta, \
    show_package_summary


def artifact_hash(artifact_bytes: bytes) -> str:
    return sha256(artifact_bytes).hexdigest()


def show_subdeployments(dabl_meta: 'PackageMetadata', contents):
    subdeployments = dabl_meta.subdeployments

    if len(subdeployments or []) > 0:
        print('\nSubdeployments:')

        for sd in subdeployments:
            sd_data = contents.get(sd)

            status = "MISSING" if (sd_data is None) \
                else f'{len(sd_data)} bytes, {artifact_hash(sd_data)}'

            print(f'   {sd} ({status})')
    else:
        print('\nSubdeployments: None')


def subcommand_main(dit_filename: str):
    if not os.path.exists(dit_filename):
        die(f'DIT file not found: {dit_filename}')

    contents = {}

    with ZipFile(dit_filename, 'a') as ditfile:
        filenames = set(ditfile.namelist())

        for zi in ditfile.infolist():
            contents[zi.filename] = ditfile.read(zi)

    try:
        dabl_meta = accept_dabl_meta(contents[DABL_META_NAME])

        show_package_summary(dabl_meta)
        show_subdeployments(dabl_meta, contents)

    except KeyError:
        die(f'DIT file missing metadata ({DABL_META_NAME} missing): {dit_filename}')


def setup(sp):
    sp.add_argument('dit_filename', metavar='dit_filename')
    return subcommand_main
