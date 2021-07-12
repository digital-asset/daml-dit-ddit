import os
import json
import subprocess
import yaml
from dataclasses import replace
from typing import Optional, Sequence
from datetime import date

from pathlib import Path

from zipfile import ZipFile

from dazl.damlast.lookup import parse_type_con_name
from dazl.damlast.util import package_ref

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
    DIT_META_NAME, \
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
    with_catalog, \
    PYTHON_REQUIREMENT_FILE, \
    daml_yaml_version, \
    load_daml_yaml


IF_PROJECT_NAME = 'daml-dit-if'


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

def build_pex(pex_filename: str, local_only: bool) -> str:
    pex_builder = PEXBuilder(include_tools=True)

    pex_builder.info.inherit_path = InheritPath.FALLBACK

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

    daml_dit_if_bundled = False

    try:
        if os.path.isfile(PYTHON_REQUIREMENT_FILE):
            LOG.info(f'Bundling dependencies from {PYTHON_REQUIREMENT_FILE}...')
            requirement_files=[PYTHON_REQUIREMENT_FILE]
        else:
            LOG.info(f'No dependency file found ({PYTHON_REQUIREMENT_FILE}), no dependencies will be bundled.')
            requirement_files=[]

        resolveds = resolve_multi(
            requirements=[],
            requirement_files=requirement_files,
            platforms=platforms)

        for resolved_dist in resolveds:

            if resolved_dist.distribution.project_name == IF_PROJECT_NAME \
               and not daml_dit_if_bundled:

                LOG.warn(f'Bundling {IF_PROJECT_NAME} in output DIT file. This will'
                         f' override the version provided by Daml Hub, potentially'
                         f' compromising compatibility of this integration with'
                         f' future updates to Daml Hub. Use this option with caution.')
                daml_dit_if_bundled = True

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

    # Entry point verification is disabled because ddit does not
    # formally depend on the integration framework, and it is not
    # necessarily available at integration build time. Because entry
    # point verification happens in ddit's environment and the
    # entrypoint is in the framework, this causes entry point
    # verification to fail unless some other agent has installed
    # daml-dit-if into ddit's environment.
    #
    # Virtual environments provide a way to work around this (and are
    # used in 'ddit run') but the PEX API does not allow a virtual
    # environment to be specified at build time. If this ever changes,
    # the build subcommand should be modified to prepare a virtual
    # enviroment for the build that contains the appropriate version
    # of daml-dit-if and entrypoint verification should be re-enabled.
    pex = PEX(
        pex_builder.path(),
        interpreter=pex_builder.interpreter,
        verify_entry_point=False)

    LOG.info('Building intermediate PEX file...')

    LOG.debug('PEX info: %r', pex_builder.info)

    pex_builder.build(
        pex_filename,
        bytecode_compile=True,
        deterministic_timestamp=True)

    if daml_dit_if_bundled:
        return 'python-direct'
    else:
        return 'python-direct-hub-if'


def build_dar(base_filename: str, dar_version: str, rebuild_dar: bool) -> 'Optional[str]':

    if load_daml_yaml() is None:
        LOG.info(f'No Daml model found, skipping DAR build.')
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
        force_integration: bool,
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
        LOG.info('Skipping DAR build (--skip-dar-build specified, no Daml model'
                 ' information will be availble in build.)')
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

    integration_runtime = 'python-direct'

    is_integration = len(integration_types) > 0

    if is_integration:
        LOG.warn('Integration types found in project - building as integration.'
                 ' Authorization will be required to install in Daml Hub.')
        integration_runtime = build_pex(tmp_filename, local_only)

    elif local_only:
        die(f'--local-only may just be used on integration builds. (Builds with'
            f' integration types defined in project.)')

    if force_integration and not is_integration:
        die(f'--integration build specified with no integration types defined.')

    subdeployments = [
        *(dabl_meta.subdeployments or []),
        *[os.path.basename(sd_filename)
          for sd_filename
          in add_subdeployments]
    ]

    icon_file = None if dabl_meta.catalog is None else dabl_meta.catalog.icon_file

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

        if icon_file and os.path.isfile(icon_file):
            pex_write(pexfile, icon_file)
            resource_files.add(icon_file)

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
            integration_types=[normalize_integration_type(ittype, integration_runtime, daml_model_info)
                               for ittype
                               in (dabl_meta.integration_types or [])])

        # Write metadata under two names to account for both old and new
        # conventions.
        yaml_filebytes = package_meta_yaml(dabl_meta)
        pex_writestr(pexfile, DIT_META_NAME, filebytes=yaml_filebytes)
        pex_writestr(pexfile, DABL_META_NAME, filebytes=yaml_filebytes)

    for subdeployment in subdeployments:
        if subdeployment not in resource_files:
            die(f'Subdeployment {subdeployment} not available in DIT file resources: {resource_files}')

    if icon_file and icon_file not in resource_files:
        die(f'Icon {icon_file} not available in DIT file resources: {resource_files}')

    os.rename(tmp_filename, dit_filename)

    dit_file_contents = read_binary_file(dit_filename)

    LOG.info('Artifact hash: %r', artifact_hash(dit_file_contents))


def normalize_integration_type(
        itype: 'IntegrationTypeInfo', runtime: str, daml_model_info: 'Optional[DamlModelInfo]'
) -> 'IntegrationTypeInfo':

    if itype.runtime:
        LOG.warn(f'Explicit integration type runtime {itype.runtime} ignored'
                 f' for integration ID {itype.id}. This field does not need to'
                 f' be specified.')

    updates = {
        # Runtime is currently fixed at python direct, and is
        # controlled by the ddit build process anyway, so makes sense
        # to populate here.
        'runtime': runtime
    }

    if itype.instance_template:
        if daml_model_info is None:
            # This could be fixed by adding another option to
            # explicitly bind a Daml model even when ddit is not
            # managind the Daml model build.
            die(f'Instance templates cannot be used with --skip-dar-build, due to lack of'
                f'Daml model info.')

        if itype.instance_template == '*':
            die(f'Integration type instance templates cannot be a wildcard and must'
                f' explicitly specify a template.')

        package = package_ref(parse_type_con_name(itype.instance_template))

        if package == '*':
            updates['instance_template'] = f'{daml_model_info.main_package_id}:{itype.instance_template}'

    return replace(itype, **updates)


def setup(sp):
    sp.add_argument('--integration', help='Require the DIT file be built as an integration. '
                    'DA approval required to deploy.',
                    dest='force_integration', action='store_true', default=False)

    sp.add_argument('--force', help='Forcibly overwrite target files if they exist',
                    dest='force', action='store_true', default=False)

    sp.add_argument('--skip-dar-build',
                    help=f'Skip the DAR build, even if there is a Daml model project present.',
                    dest='skip_dar_build', action='store_true', default=False)

    sp.add_argument('--rebuild-dar', help='Rebuild and overwrite the DAR if it already exists',
                    dest='rebuild_dar', action='store_true', default=False)

    sp.add_argument('--local-only', help='Build a local-only DIT that will not run in cluster.',
                    dest='local_only', action='store_true', default=False)

    sp.add_argument('--subdeployment', help='Add one or more subdeployments, by name, to the DIT file.',
                    nargs='+', dest='add_subdeployments', default=[])

    return subcommand_main
