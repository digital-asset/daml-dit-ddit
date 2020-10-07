import datetime
from dataclasses import dataclass, field
from typing import Optional, Sequence

def _empty_tags() -> 'Sequence[str]':
    return list()


@dataclass(frozen=True)
class IntegrationTypeFieldInfo:
    id: str
    name: str
    description: str
    field_type: str
    help_url: 'Optional[str]' = None
    default_value: 'Optional[str]' = None
    required: 'Optional[bool]' = True


@dataclass(frozen=True)
class IntegrationTypeInfo:
    artifact_hash: 'Optional[str]'
    id: str
    name: str
    description: str
    fields: 'Sequence[IntegrationTypeFieldInfo]'
    entrypoint: str
    env_class: 'Optional[str]'
    runtime: 'Optional[str]' = 'python-file'
    help_url: 'Optional[str]' = None
    instance_template: 'Optional[str]' = None


@dataclass(frozen=True)
class CatalogInfo:
    name: str
    version: str
    description: str
    release_date: 'Optional[datetime.date]'
    author: 'Optional[str]'
    url: 'Optional[str]'
    email: 'Optional[str]'
    license: 'Optional[str]'
    experimental: 'Optional[bool]'
    demo_url: 'Optional[str]'
    source_url: 'Optional[str]'
    tags: 'Sequence[str]' = field(default_factory=_empty_tags)
    short_description: 'Optional[str]' = None
    group_id: 'Optional[str]' = None
    icon_file: 'Optional[str]' = None


DABL_META_NAME = 'dabl-meta.yaml'


@dataclass(frozen=True)
class PackageMetadata:
    catalog: 'Optional[CatalogInfo]'
    subdeployments: 'Optional[Sequence[str]]'
    integration_types: 'Optional[Sequence[IntegrationTypeInfo]]'

    # Deprecated in favor of integration_types
    integrations: 'Optional[Sequence[IntegrationTypeInfo]]'
