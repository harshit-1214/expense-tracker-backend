"""Schemas for expense categories."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]


class CategoryCreate(BaseModel):
    """Body of POST /categories."""

    name: CategoryName
    description: str | None = Field(default=None, max_length=255)


class CategoryUpdate(BaseModel):
    """Body of PATCH /categories/{id}. Only the fields you send are changed."""

    name: CategoryName | None = None
    description: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def name_cannot_be_null(self) -> "CategoryUpdate":
        # Leaving `name` out is fine; sending "name": null is not.
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class CategorySummary(BaseModel):
    """Small version of a category, nested inside expense responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
