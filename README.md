# daml-dit-ddit

`ddit` is a command line tool that streamlines and automates the
process of building composite artifacts for
[Daml Hub](https://hub.daml.com/). A composite artifact is a
collection of multiple single artifacts packaged into a
[DIT file](https://github.com/digital-asset/daml-dit-api).
Artifacts in a DIT file can include Daml Models and Triggers,
Python Bots, Custom UI code, and Integration Types. Daml Hub
uses DIT files to package sample applications, libraries, and
integrations into a single deployable entity.

# Installing `ddit`

`ddit` is a Python executable distributed via the
[PyPI](https://pypi.org/project/daml-dit-ddit/) package index. Given a
Python installation of version 3.7 or later, `ddit` can be installed
using `pip3`:

```sh
$ pip3 install daml-dit-ddit
```

Once installed, verify `ddit` by launching it without arguments:

```sh
$ ddit
usage: ddit [-h] [--verbose] {build,clean,ditversion,genargs,inspect,install,publish,release,run,show,targetname} ...

positional arguments:
  {build,clean,ditversion,genargs,inspect,install,publish,release,run,show,targetname}
                        subcommand
    build               Build a DIT file.
    clean               Resets the local build target and virtual environment to an empty state.
    ditversion          Print the current version in dabl-meta.yaml
    genargs             Write a template integration argfile to stdout
    inspect             Inspect the contents of a DIT file.
    install             Install the DIT file's dependencies into a local virtual environment.
    publish             Tag and release the current DIT file.
    release             Tag and release the current DIT file.
    run                 Run the current project as an integration.
    show                Verify and print the current metadata file.
    targetname          Print the build target filename to stdout

optional arguments:
  -h, --help            show this help message and exit
  --verbose             Turn on additional logging.
2021-06-30T13:20:33-0500 [ERROR] (ddit) Fatal Error: Subcommand missing.
```

# `ddit` Project structure

In common with other build tools, `ddit` exposes its interface via a
set of subcommands and operates in project directories with a standard
layout. There are three requirements for a `ddit` project directory:

* `dabl-meta.yaml` - A metadata file at the root of the project that
  contains information on the contents of the project. (Name, version,
  URL links, etc.)
* `pkg/` - A subdirectory containing resources and files that will be
  included in the output DIT.
* An optional Daml model build, also at the project root. (`daml.yaml`
  and a source directory.)

## `dabl-meta.yaml`

Every project has a `dabl-meta.yaml` file at its root. The format of
the file is defined in [`daml-dit-api`](https://github.com/digital-asset/daml-dit-api/blob/master/daml_dit_api/package_metadata.py), and a typical example
looks like this:

```yaml
catalog:
    name: openwork-board
    version: 3.2.2
    short_description: OpenWork Board
    description: A privacy-focused Kanban board.
    author: Digital Asset (Switzerland) GmbH
    url: https://github.com/digital-asset/danban
    license: Apache-2.0
    demo_url: https://board.opensaasame.org/
    tags: [application]
    icon_file: danban-icon.png
```

Available catalog fields include the following:

| Field | Description |
|-------|-------------|
| `name` | Machine-readable name for the project. All DIT files with the same project name are considered to be different versions of the same project. |
| `version` | The version number of the project |
| `short_description` | A short description of the project, displayed in the App tile on the console.|
| `description` | An optional long-form description of the project. |
| `author` | The name of the author. |
| `email` | Contract e-mail address for project support. |
| `url` | The URL to the project's home page, |
| `license` | The name of project's license. |
| `demo_url` | An optional link to a live Demonstration instance of the project. |
| `source_url` | A optional link to the project's source repository. |
| `tags` | A list of tags associated with the project. These can be used to query specific sets of artifacts from the arcade for display in the console. |
| `icon_file` | The filename for the project's icon file. This file can be either a `PNG` or `SVG` image and must be present by that name in the output DIT. By default, `ddit` will look for the icon file in the project root and include from there if found.  |

Note that there are a few other catalog fields listed in the API
source and shown in the output of `ddit inspect`. These are generally
legacy fields used in earlier versions of Daml Hub. To ensure
compatability, `ddit` will normalize the contents of `dabl-meta.yaml`
to include values for these fields (and some of these other fields can
still be specified in `dabl-meta.yaml` for their original purpose.)
These other fields (the ones not listed above) should be considered
deprecated for future use.

## `pkg/`

This is an optional directory that contains other resources to be
includued in the output DIT. 

## Daml Project

`ddit` is integrated into the
[Daml SDK]((https://docs.daml.com/getting-started/installation.html)), 
and DIT file projects can be colocated in the same directory as `daml.yaml`.
If a Daml project is present, `ddit` will automatically manage the build
of the resultant DAR and include it in the output DIT. For projects that
need more control over the DAR build process, the automatic DAR build 
can be disabled with `--skip-dar-build`.

# Building a project with `ddit`

A project can be built with `ddit build`. For examples of what this
looks like in practice, please see one of several sample applications
available through Daml Hub:

- <https://github.com/digital-asset/dablchat>
- <https://github.com/digital-asset/dablchess>
- <https://github.com/OpenSaaSame/board>

These are all built using Makefiles that manage the build of
individual artifacts within each project. `ddit` does not build user
interfaces, so the Makefile handles that aspect of the build and
delegates to `ddit` to manage build, packaging, and release of the DIT
file itself. `ddit` primarily serves to assemble packages out of
components built by other build processes. To include these sorts of
artifacts into a DIT file, `ddit build` has a `--subdeployments`
option that takes a list of other artifacts that will be included in
the DIT file and deployed as part of the DIT file deployment.

# Inspecting a DIT file.

To facilitate management of DIT files, `ddit inspect` can be used to
view a summary of the contents of a DIT file. This includes relevent
artifact hashes, information on the associated Daml model, and catalog
information for the file.

```sh
$ ddit inspect dabl-integration-core-0.9.7.dit
Artifact hash:  7663d38129c2ed47e921a99713f1ca95285b0a1ff9e0bbad3768363cc3158d15

Package Catalog:
   name : dabl-integration-core
   version : 0.9.7
   description : Timer and Loopback Integrations
   release_date : 2021-06-22
   author : Digital Asset (Switzerland) GmbH
   url : None
   email : None
   license : Apache-2.0
   experimental : False
   demo_url : None
   source_url : https://github.com/digital-asset/daml-dit-integration-core
   tags : ['integration']
   short_description : The Core Pack
   group_id : com.digitalasset
   icon_file : integration-icon.svg

Daml Model:
   Name/Version: dabl-integration-core:1.1.1
   Package ID: 779c8ad14dd7c7bce05035bbdf7e374e0a349ac501bc4289246b2eaeaef7f990

Integration Types:
   loopback - Loopback
   timer - Timer
   ledger_event_log - Ledger Event Log
   table - Table

Subdeployments:
   dabl-integration-core-1.1.1.dar (234742 bytes, 6c2b1589f5c3083114c78d195af2f1f139661c3cdfb13f4b9f143f9706576f92)
```

# Building integrations

Integration DIT files differ from applications in that they contain
code that runs inside Daml Hub with elevated permissions that enable
them to access external network connections. Integrations are the only
deployable code that has this permission. Because of these elevated
runtime rights, specific user permissions are required to deploy
integration DIT files to Daml Hub. Please contact
[Digital Asset](https://discuss.daml.com/) for more information on
deploying custom integration types into Daml Hub.

`ddit` will build an integration DIT file for projects that define
`integration_types` in their `dabl-meta.yaml` This section specifies
the integration types contained in the DIT file. When building as an
integration, the DIT file project directory gains some of the traits
of a Python project.

* Python dependencies to be included in the output DIT can be
  specified in an optional `requirements.txt` file at the root of the
  project.
* Python source for the integrations is stored in `src/`.

`ddit` provides several additional utility commands to assist
developing an integration:

* `ddit genargs` - This generates a template argument file for the
  integration to be run locally. Once generated, the template should be
  edited to include the desired configuration values.
* `ddit run` - This runs an integration locally against a locally
  running ledger.

 For more details on implementing an integration, see the
[`daml-dit-if`](https://github.com/digital-asset/daml-dit-if)
documeentation.
