from __future__ import annotations

import os

from daml_dit_api import IntegrationTypeInfo

from .common import (
    INTEGRATION_ARG_FILE,
    die,
    get_itype,
    package_meta_integration_types,
    show_integration_types,
)
from .log import LOG


def generate_argfile(integration_type: "IntegrationTypeInfo", args_file: "str"):
    with open(args_file, "w") as out:
        out.write(f"# Arguments for integration type '{integration_type.id}'\n")
        out.write("\n")
        out.write('"metadata":\n')
        for field in integration_type.fields:
            out.write(f'    "{field.id.strip()}": "{field.field_type.strip()}"\n')


def subcommand_main(integration_type_id: str, args_file: str, force: bool = False):
    if os.path.isfile(args_file):
        if force:
            LOG.info(
                f"Forcibly overwriting existing integration argument file: {args_file}"
            )
            os.remove(args_file)
        else:
            die(f"Integration argument file already exists: {args_file}")

    generate_argfile(get_itype(integration_type_id), args_file)

    LOG.info(
        f"Integration argument file created, please update with configuration"
        f" values: {args_file}"
    )


def setup(sp):
    sp.add_argument("integration_type_id", metavar="integration_type_id")

    sp.add_argument(
        "--args-file",
        help=f"Use a specified arguments file, defaults to {INTEGRATION_ARG_FILE}.",
        dest="args_file",
        action="store",
        default=INTEGRATION_ARG_FILE,
    )

    sp.add_argument(
        "--force",
        help="Forcibly overwrite argument file if it already exists.",
        dest="force",
        action="store_true",
        default=False,
    )

    return subcommand_main
