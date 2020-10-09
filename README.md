daml-dit-api
====

API definitions for integrations and other sorts of packages to be
hosted by DABL. This contains the following:

* [The definition for the package metadata format](daml_dit_api/package_metadata.py)
* [The call API for integration bots](daml_dit_api/integration_api.py)
* [A framework for simplifying the implementation of integrations](daml_dit_api/main)

# Package Metadata

At their core, DIT files are [ZIP archives](https://en.wikipedia.org/wiki/Zip_(file_format))
that follow a specific set of conventions regarding their content. The
most important of these conventions is the presence of a YAML metadata
file at the root of the archive and named `dabl-meta.yaml`. This
metadata file contains catalog information describing the contents of
the DIT, as well as any packaging details needed to successfully
deploy a DIT file into DABL. An example of a deployment instruction is
a _subdeployment_. A subdeployment instructs DABL to deploy a specific
subfile within the DIT file. A DIT file that contains an embedded DAR
file could use a subdeployment to ensure that the embedded DAR file is
deployed to the ledger when the DIT is deployed. In this way, a DIT
file composed of multiple artifacts (DARs, Bots, UI's, etc.) can be
constructed to deploy a set of artifacts to a single ledger in a
single action.

# Integrations

Integrations are a special case of DIT file that are augmented with
the ability to run as an executable within a DABL cluster. This is
done by packaging Python [DAZL bot](https://github.com/DACH-NY/dazl)
code into an [executable ZIP](https://docs.python.org/3/library/zipapp.html)
using [PEX](https://github.com/pantsbuild/pex) and augmenting tha
resulting file with the metadata and other resources needed to make it
a correctly formed DIT file.

Logically speaking, DABL integrations are DAZL bots packaged with
information needed to fit them into the DABL runtime and user
interface. The major functional contrast between a DABL integration
and a Python Bot is that the integration has the external network
access needed to connect to an outside system and the Python Bot does
not. Due to the security implications of running within DABL with
external network access, integrations can only be deployed with the
approval of DA staff.

## Developing Integrations

The easiest way to develop an integration for DABL is to use the
[framework library](daml_dit_api/main) bundled within this API
package. The integration framework presents a Python API closely
related to the DAZL bot api and ensures that integrations follow the
conventions required to integrate into DABL. The framework parses
ledger connection arguments, translates configuration metadata into a
domain object specific to the integration, and exposes the appropriate
health check endpoints required to populate the DABL integration user
interface.

_Unless you know exactly what you are doing and why you are doing it,
use the framework._

### Locally Running an integration DIT.

Because they can be directly executed by a Python interpreter,
integration DIT files can be run directly on a development machine
like any other standalone executable. By convention, integrations
accept a number of environment variables that specify key paramaters.
Integrations built with the framework use defaults for these variables
that connect to a default locally configured sandbox instance.

Available variables include the following:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DABL_HEALTH_PORT` | 8089 | Port for Health/Status HTTP endpoint |
| `DABL_INTEGRATION_METADATA_PATH` | 'int_args.yaml' | Path to local metadata file |
| `DABL_INTEGRATION_TYPE_ID` | | Type ID for the specific integration within the DIT to run |
| `DABL_LEDGER_ID` | 'cloudbox' | Ledger ID for local ledger |
| `DABL_LEDGER_URL` | `http://localhost:6865` | Address of local ledger gRPC API |

Several of these are specifically of note for local development scenarios:

* `DABL_INTEGRATION_INTEGRATION_ID` - This is the ID of the
  integration that would normally come from DABL itself. This needs to
  be provided, but the specific value doesn't matter.
* `DABL_INTEGRATION_TYPE_ID` - DIT files can contain definitions for
  multiple types of integrations. Each integration type is described
  in a `IntegrationTypeInfo` block in the `dabl-meta.yaml` file and
  identified with an `id`. This ID needs to be specified with
  `DABL_INTEGRATION_TYPE_ID`, to launch the appropriate integration
  type within the DIT.
* `DABL_INTEGRATION_METADATA_PATH` - Integration configuration
  parameters specified to the integration from the console are
  communicated to the integration at runtime via a metadata file. By
  convention, this metadata file is named `int_args.yaml` and must be
  located in the working directory where the integration is being run.
* `DABL_HEALTH_PORT` - Each integration exposes health and status over
  a `healthz` HTTP resource. <http://localhost:8089/healthz> is the
  default, and the port can be adjusted, if necessary. (This will be
  the case in scenarios where multiple integrations are being run
  locally.) Inbound webhook resources defined with webhook handlers
  will also be exposed on this HTTP endpoint.

### Integration Configuration Arguments

Integrations accept their runtime configuration parameters through the
metadata block of a configuration YAML file. This file is distinct
from `dabl_meta.yaml`, usually named `int_args.yaml` and by default
should be located in the working directory of the integration. A file
and path can be explicitly specified using the
`DABL_INTEGRATION_METADATA_PATH` environment variable.

The format of the file is a single string/string map located under the
`metadata` key. The keys of the metadata map are the are defined by
the `field`s specified for the integration in the DIT file's
`dabl-meta.yaml` and the values are the the configuration paramaters
for the integration.

```yaml
"metadata":
  "interval": "1"
  "runAs": "ledger-party-f18044e5-6157-47bd-8ba6-7641b54b87ff"
  "targetTemplate": "9b0a268f4d5c93831e6b3b6d675a5416a8e94015c9bde7263b6ab450e10ae11b:Utility.Sequence:Sequence"
  "templateChoice": "Sequence_Next"
```
