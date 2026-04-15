from __future__ import annotations

from app.api.schemas.common import OpenSchemaModel


class ModelPricingLine(OpenSchemaModel):
    label: str
    value: str


class ModelPricingSnapshot(OpenSchemaModel):
    currency: str | None = None
    billing_unit: str | None = None
    price_lines: list[ModelPricingLine]


class ModelAvailabilitySnapshot(OpenSchemaModel):
    window: str
    sample_count: int
    success_rate: float


class ModelPricingItem(OpenSchemaModel):
    model_code: str
    display_name: str
    category: str
    summary: str
    supported_input_modes: list[str]
    pricing: ModelPricingSnapshot
    availability: ModelAvailabilitySnapshot | None = None
