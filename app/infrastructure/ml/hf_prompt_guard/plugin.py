from app.infrastructure.ml.common.model_artifacts import TextClassificationArtifact
from app.infrastructure.ml.common.transformers_text_classifier import (
    TransformersTextClassificationAdapter,
)


def build_hf_prompt_guard_classifier(
    *,
    pipeline_factory=None,
) -> TransformersTextClassificationAdapter:
    return TransformersTextClassificationAdapter(
        TextClassificationArtifact(
            model_code="hf_prompt_guard",
            product_name="HF Prompt Guard",
            model_name="Prompt safety transformer adapter",
            model_id_or_path="meta-llama/Prompt-Guard-86M",
            model_version="hf-prompt-guard-adapter-v1",
            task_type="prompt_safety",
            supported_modes=["standard"],
            labels=["safe", "prompt_injection", "jailbreak"],
            label_mapping={
                "LABEL_0": "safe",
                "LABEL_1": "prompt_injection",
                "LABEL_2": "jailbreak",
            },
            default_risk_level="high",
            default_recommended_action="review",
        ),
        pipeline_factory=pipeline_factory,
    )
