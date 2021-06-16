import os
import json
import subprocess
import yaml
from dataclasses import replace
from typing import Optional, Sequence
from datetime import date

from pathlib import Path

from zipfile import ZipFile

from pex.pex import PEX

from pex.pex_builder import \
    PEXBuilder

from pex.inherit_path import \
    InheritPath

from pex.resolver import \
    Unsatisfiable, \
    parsed_platform, \
    resolve_multi

from daml_dit_api import \
    DABL_META_NAME, \
    DamlModelInfo, \
    IntegrationTypeInfo

from .log import LOG

from .common import \
    die, \
    artifact_hash, \
    load_dabl_meta, \
    package_meta_yaml, \
    package_dit_basename, \
    package_dit_filename, \
    package_meta_integration_types, \
    read_binary_file, \
    with_catalog


def check_target_file(filename: str, force: bool):
    if os.path.exists(filename):
        if force:
            os.remove(filename)
        else:
            die(f'Target file already exists: {filename}')

def pex_writestr(pex: 'ZipFile', filepath: str, filebytes: bytes):
    if filepath in pex.namelist():
        LOG.warn(f'  File {filepath} exists in archive -- skipping.')
    else:
        pex.writestr(filepath, filebytes)

def pex_write(pex: 'ZipFile', filepath: str, arcname: 'Optional[str]' = None):
    filename = filepath.split("/")[-1]
    if filename in pex.namelist():
        LOG.warn(f'  File {filename} exists in archive -- skipping.')
    else:
        pex.write(filepath, arcname=arcname)

def build_pex(pex_filename: str, local_only: bool):
    pex_builder = PEXBuilder(include_tools=True)

    pex_builder.info.inherit_path = InheritPath.PREFER

    pex_builder.set_entry_point('daml_dit_if.main:main')
    pex_builder.set_shebang('/usr/bin/env python3')


    platforms = [
        parsed_platform('current')
    ]

    if local_only:
        LOG.warn('Local-only build. THIS DIT WILL NOT RUN IN DAML HUB.')
    else:
        platforms = [
            *platforms,
            parsed_platform('manylinux2014_x86_64-cp-38-cp38')
        ]

    try:
        LOG.info('Resolving dependencies...')

        resolveds = resolve_multi(
            requirements=[],
            requirement_files=['requirements.txt'],
            platforms=platforms)

        for resolved_dist in resolveds:
            LOG.debug("req: %s", resolved_dist.distribution)
            LOG.debug("     -> target: %s", resolved_dist.target)

            pex_builder.add_distribution(resolved_dist.distribution)
            if resolved_dist.direct_requirement:
                LOG.info("direct_req: %s", resolved_dist.direct_requirement)
                LOG.debug("     -> target: %s", resolved_dist.target)

                pex_builder.add_requirement(resolved_dist.direct_requirement)


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

    LOG.debug('PEX info: %r', pex_builder.info)

    pex_builder.build(
        pex_filename,
        bytecode_compile=True,
        deterministic_timestamp=True)

DAML_YAML_NAME = 'daml.yaml'

def daml_yaml_version():
    with open(DAML_YAML_NAME, "r") as f:
        daml_yaml = yaml.safe_load(f.read())

        LOG.debug(f'{DAML_YAML_NAME}: %r', daml_yaml)

        if 'version' in daml_yaml:
            version = daml_yaml['version']
            LOG.info(f'Daml model version from {DAML_YAML_NAME}: %r', version)
            return version
        else:
            die(f'No model version specified in {DAML_YAML_NAME}')


def build_dar(base_filename: str, dar_version: str, rebuild_dar: bool) -> 'Optional[str]':
    if not os.path.exists(DAML_YAML_NAME):
        LOG.info(f'No {DAML_YAML_NAME} found, skipping DAR build.')
        return None

    dar_filename = f'{base_filename}-{dar_version}.dar'

    if os.path.exists(dar_filename):
        if rebuild_dar:
            LOG.warn(f'>>>>> REPLACING EXISTING DAR: {dar_filename}.')
            os.remove(dar_filename)
        else:
            LOG.info(f'Retaining existing DAR: {dar_filename}.')
            return dar_filename

    LOG.info(f'Building DAR file: {dar_filename}')

    completed = subprocess.run(['daml', 'build', '-o', dar_filename])

    if completed.returncode != 0:
        die(f'Error building DAR file, rc={completed.returncode}')

    return dar_filename


def get_dar_main_package_id(dar_filename: str) -> str:

    completed = subprocess.run(
        ['daml', 'damlc', 'inspect-dar', '--json', dar_filename],
        capture_output=True, text=True)

    if completed.returncode != 0:
        die(f'Error inspecting DAR for package ID, rc={completed.returncode} error output:\n{completed.stderr}')

    dar_inspect_text = completed.stdout

    try:
        dar_inspect_results = json.loads(dar_inspect_text)

        main_package_id = dar_inspect_results['main_package_id']
    except:
        LOG.exception('Error parsing DAR metadata for main package ID, Text:\n%r', dar_inspect_text)
        die('Error parsing DAR metadata for main package ID')

    return main_package_id


def subcommand_main(
        is_integration: bool,
        force: bool,
        skip_dar_build: bool,
        rebuild_dar: bool,
        local_only: bool,
        add_subdeployments: 'Sequence[str]'):

    dabl_meta = load_dabl_meta()

    integration_types = package_meta_integration_types(dabl_meta)

    base_filename = package_dit_basename(dabl_meta)

    tmp_filename = f'{base_filename}.tmp'

    dit_filename = package_dit_filename(dabl_meta)

    if os.path.exists(tmp_filename):
        LOG.warn(f'Deleting temporary file: {tmp_filename}')
        os.remove(tmp_filename)

    check_target_file(dit_filename, force)

    for sd_filename in add_subdeployments:
        if not os.path.exists(sd_filename):
            die(f'Additional subdeployment file not found to be added: {sd_filename}')

    LOG.info(f'Building {dit_filename}')

    daml_model_info = None

    if skip_dar_build:
        LOG.info('Skipping DAR build (--skip-dar-build specified)')
        dar_filename = None
    else:
        catalog = with_catalog(dabl_meta)

        dar_version = daml_yaml_version()

        dar_filename = build_dar(catalog.name, dar_version, rebuild_dar)

        if dar_filename:
            main_package_id = get_dar_main_package_id(dar_filename)

            daml_model_info = DamlModelInfo(
                name = catalog.name,
                version=dar_version,
                main_package_id=main_package_id)

            LOG.info('Main package ID: %r', main_package_id)

    if is_integration:
        if not len(integration_types):
            die('daml-meta.yaml does not specify integration types and therefore '
                'cannot be built with --integration')

        LOG.warn('Building as integration. Authorization will be required to install in Daml Hub.')
        build_pex(tmp_filename, local_only)

    else:
        if len(integration_types):
            die('daml-meta.yaml specifies integration types and therefore '
                'must be built with --integration')

        if local_only:
            die('--local-only may just be used on builds with --integration '
                'specified.')

    subdeployments = [
        *(dabl_meta.subdeployments or []),
        *[os.path.basename(sd_filename)
          for sd_filename
          in add_subdeployments]
    ]

    resource_files = set()

    LOG.info('Enriching output DIT file...')
    with ZipFile(tmp_filename, 'a') as pexfile:

        if os.path.isdir('pkg'):
            for pkg_filename in os.listdir('pkg'):
                resource_files.add(pkg_filename)
                file_bytes = Path(f'pkg/{pkg_filename}').read_bytes()

                LOG.info(f'  Adding package file: {pkg_filename}, len=={len(file_bytes)}')
                pex_writestr(pexfile, pkg_filename, file_bytes)
        else:
            LOG.info('No pkg directory found, not adding any resources.')

        for sd_filename in add_subdeployments:
            arcname=os.path.basename(sd_filename)
            resource_files.add(arcname)
            LOG.info(f'  Adding package file: {sd_filename} as {arcname}')
            pex_write(pexfile, sd_filename, arcname=arcname)

        if dar_filename:
            pex_write(pexfile, dar_filename)
            resource_files.add(dar_filename)

            subdeployments=[*subdeployments, dar_filename]

        dabl_meta = replace(
            dabl_meta,
            catalog=replace(dabl_meta.catalog,
                            release_date=date.today()),
            daml_model=daml_model_info,
            subdeployments=subdeployments,
            integration_types=[normalize_integration_type(ittype)
                               for ittype
                               in (dabl_meta.integration_types or [])])

        pex_writestr(pexfile, DABL_META_NAME, filebytes=package_meta_yaml(dabl_meta))

    for subdeployment in subdeployments:
        if subdeployment not in resource_files:
            die(f'Subdeployment {subdeployment} not available in DIT file resources: {resource_files}')

    icon_file = None if dabl_meta.catalog is None else dabl_meta.catalog.icon_file

    if icon_file and icon_file not in resource_files:
        die(f'Icon {icon_file} not available in DIT file resources: {resource_files}')

    os.rename(tmp_filename, dit_filename)

    dit_file_contents = read_binary_file(dit_filename)

    LOG.info('Artifact hash: %r', artifact_hash(dit_file_contents))


def normalize_integration_type(itype: 'IntegrationTypeInfo') -> 'IntegrationTypeInfo':

    if itype.runtime:
        LOG.warn(f'Explicit integration type runtime {itype.runtime} ignored'
                 f' for integration ID {itype.id}. This field does not need to'
                 f' be specified.')

    # Runtime is currently fixed at python direct, and is controlled
    # by the ddit build process anyway, so makes sense to populate here.
    return replace(itype, runtime='python-direct')


def setup(sp):

    sp.add_argument('--integration', help='Build DIT file with integration support. '
                    'DA approval requried to deploy.',
                    dest='is_integration', action='store_true', default=False)

    sp.add_argument('--force', help='Forcibly overwrite target files if they exist',
                    dest='force', action='store_true', default=False)

    sp.add_argument('--skip-dar-build',
                    help=f'Skip the DAR build, even if there is a {DAML_YAML_NAME}.',
                    dest='skip_dar_build', action='store_true', default=False)

    sp.add_argument('--rebuild-dar', help='Rebuild and overwrite the DAR if it already exists',
                    dest='rebuild_dar', action='store_true', default=False)

    sp.add_argument('--local-only', help='Build a local-only DIT that will not run in cluster.',
                    dest='local_only', action='store_true', default=False)

    sp.add_argument('--subdeployment', help='Add one or more subdeployments, by name, to the DIT file.',
                    nargs='+', dest='add_subdeployments', default=[])

    return subcommand_main
