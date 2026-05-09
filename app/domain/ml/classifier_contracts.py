from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClassificationInput:
    text: str
    model_code: str
    mode: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ClassificationOutput:
    label: str
    confidence: float
    risk_level: str
    recommended_action: str
    explanation: str | None = None
    raw_scores: dict[str, float] | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelDescriptor:
    model_code: str
    product_name: str
    model_name: str
    model_version: str
    task_type: str
    supported_modes: list[str]
    labels: list[str]
    pricing: dict[str, int]


class BaseClassifier(ABC):
    model_code: str
    product_name: str
    model_name: str
    model_version: str
    task_type: str
    supported_modes: list[str]
    labels: list[str]

    @abstractmethod
    def predict(self, input_data: ClassificationInput) -> ClassificationOutput:
        """Return a normalized classification output."""

    def describe(self, pricing: dict[str, int] | None = None) -> ModelDescriptor:
        return ModelDescriptor(
            model_code=self.model_code,
            product_name=self.product_name,
            model_name=self.model_name,
            model_version=self.model_version,
            task_type=self.task_type,
            supported_modes=self.supported_modes,
            labels=self.labels,
            pricing=pricing or {},
        )
