from collections.abc import Callable
from typing import Any

from app.domain.ml.classifier_contracts import (
    BaseClassifier,
    ClassificationInput,
    ClassificationOutput,
)
from app.infrastructure.ml.common.model_artifacts import TextClassificationArtifact


class TransformersTextClassificationAdapter(BaseClassifier):
    def __init__(
        self,
        artifact: TextClassificationArtifact,
        *,
        pipeline_factory: Callable[..., Any] | None = None,
    ) -> None:
        artifact.validate()
        self.artifact = artifact
        self.model_code = artifact.model_code
        self.product_name = artifact.product_name
        self.model_name = artifact.model_name
        self.model_version = artifact.model_version
        self.task_type = artifact.task_type
        self.supported_modes = artifact.supported_modes
        self.labels = artifact.labels
        self._pipeline_factory = pipeline_factory
        self._pipeline = None

    def predict(self, input_data: ClassificationInput) -> ClassificationOutput:
        rows = self._get_pipeline()(input_data.text)
        row = self._select_top_row(rows)
        source_label = str(row["label"])
        label = self.artifact.label_mapping.get(source_label, source_label)
        confidence = float(row["score"])
        return ClassificationOutput(
            label=label,
            confidence=confidence,
            risk_level=self.artifact.default_risk_level,
            recommended_action=self.artifact.default_recommended_action,
            explanation=f"Transformer classifier selected source label {source_label}.",
            raw_scores={label: confidence},
            metadata={
                "source_label": source_label,
                "model_id_or_path": self.artifact.model_id_or_path,
                "revision": self.artifact.revision,
            },
        )

    def _get_pipeline(self):
        if self._pipeline is None:
            factory = self._pipeline_factory or self._default_pipeline_factory
            kwargs = {
                "task": "text-classification",
                "model": self.artifact.model_id_or_path,
                "top_k": None,
            }
            if self.artifact.revision is not None:
                kwargs["revision"] = self.artifact.revision
            self._pipeline = factory(**kwargs)
        return self._pipeline

    @staticmethod
    def _default_pipeline_factory(**kwargs):
        from transformers import pipeline

        return pipeline(**kwargs)

    @staticmethod
    def _select_top_row(rows) -> dict:
        if isinstance(rows, list) and rows and isinstance(rows[0], list):
            rows = rows[0]
        if not isinstance(rows, list) or not rows:
            raise ValueError("Pipeline returned no classification rows")
        return max(rows, key=lambda row: float(row["score"]))
