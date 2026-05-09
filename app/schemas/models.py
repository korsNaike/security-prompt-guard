from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    model_code: str
    product_name: str
    model_name: str
    version: str = Field(serialization_alias="model_version")
    task_type: str
    supported_modes: list[str]
    labels: list[str]
    pricing: dict[str, int]


class ModelListResponse(BaseModel):
    items: list[ModelInfo]
