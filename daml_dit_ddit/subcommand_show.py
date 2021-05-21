from .common import \
    load_dabl_meta, \
    show_package_summary


def subcommand_main():
    dabl_meta = load_dabl_meta()

    show_package_summary(dabl_meta)


def setup(sp):
    return subcommand_main
