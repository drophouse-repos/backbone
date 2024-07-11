from pydantic import StringConstraints, BaseModel, Field
from typing import List, Dict
from typing_extensions import Annotated

class ApparelColor(BaseModel):
    asset: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Color asset", description="Color asset is required."
    )
    clip: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Color clip", description="Color clip is required."
    )
    color_map: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Color map", description="Color map is required."
    )

class Apparel(BaseModel):
    apparel: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Product apparel", description="Product apparel is required."
    )
    description: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Product description", description="Product description is required."
    )
    default_color: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Product default_color", description="Product default_color is required."
    )
    sizes: List[str]
    colors: Dict[str, ApparelColor]

class OrganizationModel(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Organization name", description="Organization name is required."
    )
    org_id: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Organization ID", description="Organization ID is required."
    )
    mask: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Organization Mask", description="Organization Mask is required."
    )
    logo: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Organization logo", description="Organization logo is required."
    )
    theme_color: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Organization theme_color", description="Organization theme_color is required."
    )
    font: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Organization font", description="Organization font is required."
    )
    favicon: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="Organization favicon", description="Organization favicon is required."
    )
    products: List[Apparel]