import io
import os

from typing import Dict
from zipfile import ZipFile

from daml_dit_api import \
    DIT_META_NAMES, \
    PackageMetadata

from .common import \
    die, \
    artifact_hash, \
    accept_dabl_meta_bytes, \
    read_binary_file, \
    show_package_summary

from .log import LOG


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

    dabl_meta = None

    for subfile_name in DIT_META_NAMES:
        meta_contents = contents.get(subfile_name)

        if meta_contents:
            if dabl_meta:
                LOG.debug(f' Additional metadata subfile ignored: {subfile_name}. (This'
                          f' is expected in DIT files built to be compatible with'
                          f' both the old and new metadata filenames.)')

            dabl_meta = accept_dabl_meta_bytes(contents[subfile_name])

    if dabl_meta is None:
        die(f'DIT file missing metadata ({DIT_META_NAMES[0]} missing): {dit_filename}')

    show_package_summary(dabl_meta)
    show_subdeployments(dabl_meta, contents)


def setup(sp):
    sp.add_argument('dit_filename', metavar='dit_filename')
    return subcommand_main
