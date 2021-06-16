import io
import os

from typing import Dict
from zipfile import ZipFile

from daml_dit_api import \
    DABL_META_NAME, \
    PackageMetadata

from .common import \
    die, \
    artifact_hash, \
    accept_dabl_meta, \
    read_binary_file, \
    show_package_summary


def show_subdeployments(dabl_meta: 'PackageMetadata', contents):
    subdeployments = dabl_meta.subdeployments

    if subdeployments is not None and len(subdeployments) > 0:
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

    contents : Dict[str, bytes] = {}

    dit_file_contents = read_binary_file(dit_filename)

    print('Artifact hash: ', artifact_hash(dit_file_contents))
    print()

    with ZipFile(io.BytesIO(dit_file_contents), 'r') as ditfile:
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
