from app.domain.ml.classifier_contracts import ClassificationOutput
from app.infrastructure.cache.classification_cache import (
    CachedClassificationResult,
    InMemoryClassificationCache,
)


def test_cache_key_normalizes_whitespace_and_case() -> None:
    cache = InMemoryClassificationCache()

    first = cache.build_key(model_code="prompt_guard", mode="standard", text=" Hello   WORLD ")
    second = cache.build_key(model_code="prompt_guard", mode="standard", text="hello world")

    assert first == second


def test_cached_result_round_trips_to_classification_output() -> None:
    cached = CachedClassificationResult.from_output(
        output=ClassificationOutput(
            label="safe",
            confidence=0.8,
            risk_level="low",
            recommended_action="allow",
            metadata={"source": "test"},
        ),
        model_code="prompt_guard",
        model_version="baseline-rules-v1",
    )

    output = cached.to_output()

    assert output.label == "safe"
    assert output.metadata == {"source": "test", "cache_hit": True}
