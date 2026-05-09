from app.core.config import settings
from app.domain.ml.model_registry import ModelRegistry
from app.infrastructure.ml.config_loader import instantiate_classifier, load_model_definitions


def build_model_registry(config_path: str | None = None) -> ModelRegistry:
    registry = ModelRegistry()
    for definition in load_model_definitions(config_path or settings.model_config_path):
        registry.register(instantiate_classifier(definition.model_class), definition.pricing)
    return registry


model_registry = build_model_registry()
