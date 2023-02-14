from typing import List, Optional, Union

from typing_extensions import Literal

from schema_source.common import BaseModel, PassThroughProp, ResourceAttributes, get_prop

resourcereference = get_prop("sam-property-connector-resourcereference")
properties = get_prop("sam-resource-connector")

PermissionsType = List[Literal["Read", "Write"]]


class ResourceReference(BaseModel):
    Id: Optional[str] = resourcereference("Id")
    Arn: Optional[PassThroughProp] = resourcereference("Arn")
    Name: Optional[PassThroughProp] = resourcereference("Name")
    Qualifier: Optional[PassThroughProp] = resourcereference("Qualifier")
    QueueUrl: Optional[PassThroughProp] = resourcereference("QueueUrl")
    ResourceId: Optional[PassThroughProp] = resourcereference("ResourceId")
    RoleName: Optional[PassThroughProp] = resourcereference("RoleName")
    Type: Optional[str] = resourcereference("Type")


class Properties(BaseModel):
    Source: ResourceReference = properties("Source")
    Destination: Union[ResourceReference, List[ResourceReference]] = properties("Destination")
    Permissions: List[Literal["Read", "Write"]] = properties("Permissions")


class Resource(ResourceAttributes):
    Type: Literal["AWS::Serverless::Connector"]
    Properties: Properties


class SourceReference(BaseModel):
    Qualifier: Optional[PassThroughProp] = resourcereference("Qualifier")


class EmbeddedConnectorProperties(BaseModel):
    SourceReference: Optional[SourceReference]  # TODO: add docs for SourceReference
    Destination: Union[ResourceReference, List[ResourceReference]] = properties("Destination")
    Permissions: PermissionsType = properties("Permissions")


# TODO make connectors a part of all CFN Resources
class EmbeddedConnector(ResourceAttributes):
    Properties: EmbeddedConnectorProperties
