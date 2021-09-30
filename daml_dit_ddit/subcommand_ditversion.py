import semver

from .common import die, load_dabl_meta, with_catalog

def subcommand_main(
        final_version: bool):

    catalog = with_catalog(load_dabl_meta())

    version = semver.VersionInfo.parse(catalog.version)

    if final_version:
        version = version.finalize_version()

    print(str(version))


def setup(sp):
    sp.add_argument('--final-version', help='Render the version as MAJOR.MINOR.PATCH.',
                    dest='final_version', action='store_true', default=False)

    return subcommand_main
