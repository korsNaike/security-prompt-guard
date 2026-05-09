import hashlib
from dataclasses import dataclass

from app.domain.ml.classifier_contracts import ClassificationOutput


@dataclass(frozen=True)
class CachedClassificationResult:
    label: str
    confidence: float
    risk_level: str
    recommended_action: str
    explanation: str | None
    raw_scores: dict[str, float] | None
    metadata: dict | None
    model_code: str
    model_version: str

    @classmethod
    def from_output(
        cls,
        *,
        output: ClassificationOutput,
        model_code: str,
        model_version: str,
    ) -> "CachedClassificationResult":
        return cls(
            label=output.label,
            confidence=output.confidence,
            risk_level=output.risk_level,
            recommended_action=output.recommended_action,
            explanation=output.explanation,
            raw_scores=output.raw_scores,
            metadata=output.metadata,
            model_code=model_code,
            model_version=model_version,
        )

    def to_output(self) -> ClassificationOutput:
        metadata = dict(self.metadata or {})
        metadata["cache_hit"] = True
        return ClassificationOutput(
            label=self.label,
            confidence=self.confidence,
            risk_level=self.risk_level,
            recommended_action=self.recommended_action,
            explanation=self.explanation,
            raw_scores=self.raw_scores,
            metadata=metadata,
        )


class InMemoryClassificationCache:
    def __init__(self) -> None:
        self._items: dict[str, CachedClassificationResult] = {}

    def build_key(self, *, model_code: str, mode: str, text: str) -> str:
        normalized = " ".join(text.strip().split()).casefold()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"classification:{model_code}:{mode}:{digest}"

    def get(self, *, model_code: str, mode: str, text: str) -> CachedClassificationResult | None:
        return self._items.get(self.build_key(model_code=model_code, mode=mode, text=text))

    def set(
        self,
        *,
        model_code: str,
        mode: str,
        text: str,
        result: CachedClassificationResult,
    ) -> None:
        self._items[self.build_key(model_code=model_code, mode=mode, text=text)] = result

    def clear(self) -> None:
        self._items.clear()


classification_cache = InMemoryClassificationCache()
