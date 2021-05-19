# daml-dit-ddit

`ddit` is a command line tool, written in Python, to streamline and
automate the process of building composite artifacts for
[Daml Hub](https://hub.daml.com/). Daml Hub stores composite
artifacts in [DIT files](https://github.com/digital-asset/daml-dit-api),
which aggregate metadata alongside multiple deployable entities in a
single file. Daml Hub uses these to store application deployments as well
as integrations.

# Installing `ddit`

`ddit` is a Python executable built using [PEX](https://github.com/pantsbuild/pex),
and distributed via the [PyPI](https://pypi.org/project/daml-dit-ddit/) package index.

Given a Python installation of version 3.7 or later, `ddit` can be installed using `pip3`

```sh
$ pip3 install daml-dit-ddit
```

Once installed, verify `ddit` by launching it without arguments:

```sh
$ ddit
usage: ddit [-h] [--verbose] {build,ditversion,genargs,inspect,release,show,targetname} ...

positional arguments:
  {build,ditversion,genargs,inspect,release,show,targetname}
                        subcommand
    build               Build a DIT file.
    ditversion          Print the current version in dabl-meta.yaml
    genargs             Write a template integration argfile to stdout
    inspect             Inspect the contents of a DIT file.
    release             Tag and release the current DIT file.
    show                Verify and print the current metadata file.
    targetname          Print the build target filename to stdout

optional arguments:
  -h, --help            show this help message and exit
  --verbose             Turn on additional logging.
2021-02-03T19:24:31-0500 [ERROR] (ddit) Fatal Error: Subcommand missing.
```

# Using `ddit`

`ddit` is used to build two major categories of DAR files:
applications and integrations. Applications are simple composites of
one or more distinct sub-artifacts. This is useful to deploy, for
example, a Daml model alongside the Python Bots and UI code composing
the rest of the application. When building these sorts of DIT files,
`ddit` primarily serves to assemble packages out of components built
by other build processes. Put another way, `ddit` won't build your
user interface itself, it has to be built before `ddit` can package
it into a DIT file.

For examples of what this looks like in practice, please see one of
several sample applications available through Daml Hub:

- <https://github.com/digital-asset/dablchat>
- <https://github.com/digital-asset/dablchess>
- <https://github.com/OpenSaaSame/board>

These are all built using Makefiles that delegate to `ddit` to manage
packaging and release. Make runs the overall build process using `ddit ditversion` and `ddit targetname` to parse out version and name
information from `dabl-meta.yaml`, `ddit build` to package the DIT
file, and `ddit release` to release that DIT file to Github.

## Specific support for Daml

`ddit` is integrated into the Daml ecosystem and will, by default,
treat the the root build directory as a Daml project directory if
there is a `daml.yaml` file in the root. As part of `ddit build`,
`ddit` will recursively invoke the
[Daml SDK's](https://docs.daml.com/getting-started/installation.html)
`daml build` command to build the Daml model used by the DIT file.
If it is necessary to take more fine grained control over the model
build process, this can be disabled by specifying `--skip-dar-build`.

Note also that `ddit` will not rebuild a DAR file that already exists
unless `--force` is specified. This is intended to make it easier to
keep a given DAR file stable across multiple releases of the same DIT
file. If the model is stable, the DAR itself should also be stable.

# Building integrations

Integration DIT files differ from applications in that they contain
code that runs within the Daml Hub cluster that has access to both a
ledger and the external network. Because of these elevated access
rights, specific permissions are required to deploy these DIT files to
Daml Hub, and these DIT files must be built using the `--integration` flag
passed to `ddit build`.

When running in integration mode, The DIT file build directory is
considered to be a Python project. Python dependencies are specified
in `requirements.txt`, Python source code is under `src`, and the
project is built using an instance of [PEX](https://github.com/pantsbuild/pex)
that is internal to `ddit` itself.

Integration DIT files are also allowed (and required) to have an
`integration_types` section in their `dabl-meta.yaml` specifying the
integrations supported by the DIT file. This is enforced by `ddit`:
`--integration` mode is required to build DIT files that specify
integration types.
