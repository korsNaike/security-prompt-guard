from app.infrastructure.ml.hf_prompt_guard.plugin import build_hf_prompt_guard_classifier
from app.infrastructure.ml.hf_sentiment.plugin import build_hf_sentiment_classifier


def test_hf_prompt_guard_factory_builds_descriptor_without_loading_model() -> None:
    classifier = build_hf_prompt_guard_classifier(pipeline_factory=lambda **kwargs: None)

    descriptor = classifier.describe({"standard": 10})

    assert descriptor.model_code == "hf_prompt_guard"
    assert "jailbreak" in descriptor.labels
    assert descriptor.pricing == {"standard": 10}


def test_hf_sentiment_factory_builds_descriptor_without_loading_model() -> None:
    classifier = build_hf_sentiment_classifier(pipeline_factory=lambda **kwargs: None)

    descriptor = classifier.describe({"standard": 5})

    assert descriptor.model_code == "hf_sentiment"
    assert descriptor.labels == ["negative", "neutral", "positive"]
