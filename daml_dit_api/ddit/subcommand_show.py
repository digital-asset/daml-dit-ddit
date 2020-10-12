from dataclasses import asdict

from .common import load_dabl_meta, show_integration_types

def subcommand_main():
    dabl_meta = load_dabl_meta()

    print('Package Catalog:')
    for (k, v) in asdict(dabl_meta.catalog).items():
        print(f'   {k} : {v}')

    show_integration_types(dabl_meta)

def setup_argparse(sp):
    pass
