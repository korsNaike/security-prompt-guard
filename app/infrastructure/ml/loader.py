from app.domain.ml.model_registry import ModelRegistry
from app.infrastructure.ml.prompt_guard.classifier import PromptGuardClassifier
from app.infrastructure.ml.text_mood.classifier import TextMoodClassifier


def build_model_registry() -> ModelRegistry:
    registry = ModelRegistry()
    registry.register(PromptGuardClassifier(), {"basic": 3, "standard": 7, "advanced": 15})
    registry.register(TextMoodClassifier(), {"basic": 2, "standard": 5})
    return registry


model_registry = build_model_registry()
