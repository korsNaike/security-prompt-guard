from app.core.exceptions import ModelNotFoundError, UnsupportedModeError
from app.domain.ml.classifier_contracts import BaseClassifier, ModelDescriptor


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, BaseClassifier] = {}
        self._pricing: dict[str, dict[str, int]] = {}

    def register(self, classifier: BaseClassifier, pricing: dict[str, int]) -> None:
        self._models[classifier.model_code] = classifier
        self._pricing[classifier.model_code] = pricing

    def get(self, model_code: str) -> BaseClassifier:
        if model_code not in self._models:
            raise ModelNotFoundError(model_code)
        return self._models[model_code]

    def get_cost(self, model_code: str, mode: str) -> int:
        self.get(model_code)
        model_pricing = self._pricing.get(model_code, {})
        if mode not in model_pricing:
            raise UnsupportedModeError(model_code, mode)
        return model_pricing[mode]

    def describe(self, model_code: str) -> ModelDescriptor:
        classifier = self.get(model_code)
        return classifier.describe(self._pricing.get(model_code))

    def list_models(self) -> list[ModelDescriptor]:
        return [self.describe(model_code) for model_code in sorted(self._models)]
