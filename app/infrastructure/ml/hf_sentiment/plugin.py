from app.infrastructure.ml.common.model_artifacts import TextClassificationArtifact
from app.infrastructure.ml.common.transformers_text_classifier import (
    TransformersTextClassificationAdapter,
)


def build_hf_sentiment_classifier(
    *,
    pipeline_factory=None,
) -> TransformersTextClassificationAdapter:
    return TransformersTextClassificationAdapter(
        TextClassificationArtifact(
            model_code="hf_sentiment",
            product_name="HF Sentiment",
            model_name="Multilingual sentiment transformer adapter",
            model_id_or_path="cardiffnlp/twitter-xlm-roberta-base-sentiment",
            model_version="hf-sentiment-adapter-v1",
            task_type="sentiment",
            supported_modes=["standard"],
            labels=["negative", "neutral", "positive"],
            label_mapping={
                "negative": "negative",
                "neutral": "neutral",
                "positive": "positive",
                "LABEL_0": "negative",
                "LABEL_1": "neutral",
                "LABEL_2": "positive",
            },
            default_risk_level="low",
            default_recommended_action="allow",
        ),
        pipeline_factory=pipeline_factory,
    )
