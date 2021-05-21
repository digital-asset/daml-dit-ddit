from .common import load_dabl_meta

def subcommand_main():
    dabl_meta = load_dabl_meta()

    print(dabl_meta.catalog.version)


def setup(sp):
    return subcommand_main
