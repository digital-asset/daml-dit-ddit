import os
import subprocess
from dataclasses import replace
from datetime import date

from pathlib import Path

from zipfile import ZipFile

from pex.pex import PEX

from pex.pex_builder import \
    PEXBuilder

from pex.resolver import \
    Unsatisfiable, \
    parsed_platform, \
    resolve_multi

from daml_dit_api import \
    DABL_META_NAME

from .log import LOG

from .common import \
    load_dabl_meta, \
    package_meta_yaml, \
    show_integration_types, \
    die


def check_target_file(filename: str, force: bool):
    if os.path.exists(filename):
        if force:
            os.remove(filename)
        else:
            die(f'Target file already exists: {filename}')


def build_pex(pex_filename: str):
    pex_builder = PEXBuilder()

    pex_builder.info.inherit_path = True

    pex_builder.set_entry_point('daml_dit_if.main')
    pex_builder.set_shebang('/usr/bin/env python3')

    platforms = [
        parsed_platform('current'),
        parsed_platform('manylinux2014_x86_64-cp-38-cp38')
    ]

    try:
        LOG.info('Resolving dependencies...')

        resolveds = resolve_multi(
            requirements=[],
            requirement_files=['requirements.txt'],
            platforms=platforms)

        for resolved_dist in resolveds:
            LOG.debug(
                "  %s -> %s", resolved_dist.requirement, resolved_dist.distribution)

            pex_builder.add_distribution(resolved_dist.distribution)
            pex_builder.add_requirement(resolved_dist.requirement)

    except Unsatisfiable as e:
        die(f'Unsatifiable dependency error: {e}')

    def walk_and_do(fn, src_dir):
        src_dir = os.path.normpath(src_dir)
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                src_file_path = os.path.join(root, f)
                dst_path = os.path.relpath(src_file_path, src_dir)

                LOG.debug("Adding source file: %r, %r", src_file_path, dst_path)

                fn(src_file_path, dst_path)

    walk_and_do(pex_builder.add_source, 'src/')

    pex_builder.freeze(bytecode_compile=True)

    pex = PEX(
        pex_builder.path(),
        interpreter=pex_builder.interpreter,
        verify_entry_point=True)

    LOG.info('Building intermediate PEX file...')
    pex_builder.build(
        pex_filename,
        bytecode_compile=True,
        deterministic_timestamp=True)


def build_dar(base_filename: str, force: bool) -> 'Optional[str]':
    if not os.path.exists('daml.yaml'):
        return None

    dar_filename = f'{base_filename}.dar'

    check_target_file(dar_filename, force)

    LOG.info(f'Building DAR file: {dar_filename}')

    completed = subprocess.run(['daml', 'build', '-o', dar_filename])

    if completed.returncode != 0:
        die(f'Error building DAR file, rc={completed.returncode}')

    return dar_filename


def subcommand_main(force: bool):
    dabl_meta = load_dabl_meta()

    base_filename = f'{dabl_meta.catalog.name}-{dabl_meta.catalog.version}'

    tmp_filename = f'{base_filename}.tmp'
    dit_filename = f'{base_filename}.dit'

    if os.path.exists(tmp_filename):
        LOG.warn(f'Deleting temporary file: {tmp_filename}')
        os.remove(tmp_filename)

    check_target_file(dit_filename, force)

    LOG.info(f'Building {dit_filename}')

    dar_filename = build_dar(base_filename, force)
    build_pex(tmp_filename)

    LOG.info('Enriching output DIT file...')
    with ZipFile(tmp_filename, 'a') as pexfile:
        for pkg_filename in os.listdir('pkg'):
            file_bytes = Path(f'pkg/{pkg_filename}').read_bytes()

            LOG.info(f'  Adding package file: {pkg_filename}, len=={len(file_bytes)}')
            pexfile.writestr(pkg_filename, file_bytes)

        if dar_filename:
            pexfile.write(dar_filename)

            dabl_meta = replace(
                dabl_meta,
                catalog=replace(dabl_meta.catalog,
                                release_date=date.today()),
                subdeployments=[*(dabl_meta.subdeployments or []), dar_filename])

        pexfile.writestr(DABL_META_NAME, package_meta_yaml(dabl_meta))

    os.rename(tmp_filename, dit_filename)


def setup(sp):
    sp.add_argument('--force', help='Forcibly overwrite target files if they exist',
                    dest='force', action='store_true', default=False)

    return subcommand_main

