import pytest

from app.domain.ml.classifier_contracts import ClassificationInput
from app.infrastructure.ml.common.model_artifacts import TextClassificationArtifact
from app.infrastructure.ml.common.transformers_text_classifier import (
    TransformersTextClassificationAdapter,
)


def test_transformers_adapter_maps_top_pipeline_label() -> None:
    def fake_pipeline_factory(**kwargs):
        assert kwargs["model"] == "local-model"

        def pipeline(text: str):
            assert text == "hello"
            return [[{"label": "LABEL_0", "score": 0.2}, {"label": "LABEL_1", "score": 0.8}]]

        return pipeline

    adapter = TransformersTextClassificationAdapter(
        TextClassificationArtifact(
            model_code="hf_test",
            product_name="HF Test",
            model_name="Test Model",
            model_id_or_path="local-model",
            model_version="v1",
            task_type="prompt_security_classification",
            supported_modes=["standard"],
            labels=["safe", "prompt_injection"],
            label_mapping={"LABEL_0": "safe", "LABEL_1": "prompt_injection"},
            default_risk_level="low",
            default_recommended_action="allow",
        ),
        pipeline_factory=fake_pipeline_factory,
    )

    output = adapter.predict(
        ClassificationInput(text="hello", model_code="hf_test", mode="standard")
    )

    assert output.label == "prompt_injection"
    assert output.confidence == 0.8
    assert output.metadata["source_label"] == "LABEL_1"


def test_artifact_validation_rejects_missing_labels() -> None:
    artifact = TextClassificationArtifact(
        model_code="hf_test",
        product_name="HF Test",
        model_name="Test Model",
        model_id_or_path="local-model",
        model_version="v1",
        task_type="prompt_security_classification",
        supported_modes=["standard"],
        labels=[],
        label_mapping={"LABEL_0": "safe"},
    )

    with pytest.raises(ValueError, match="labels"):
        artifact.validate()
