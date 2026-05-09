from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

import yaml

from app.domain.ml.classifier_contracts import BaseClassifier


class ModelConfigError(Exception):
    pass


@dataclass(frozen=True)
class ModelDefinition:
    model_code: str
    product_name: str
    model_class: str
    version: str
    task_type: str
    labels: list[str]
    pricing: dict[str, int]


def load_model_definitions(path: str | Path) -> list[ModelDefinition]:
    config_path = Path(path)
    if not config_path.exists():
        raise ModelConfigError(f"Model config file was not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ModelConfigError(f"Invalid model config YAML: {exc}") from exc

    models = raw.get("models")
    if not isinstance(models, dict) or not models:
        raise ModelConfigError("Model config must contain non-empty `models` mapping")

    definitions: list[ModelDefinition] = []
    for model_code, payload in models.items():
        if not isinstance(payload, dict):
            raise ModelConfigError(f"Model `{model_code}` must be a mapping")
        modes = payload.get("modes")
        if not isinstance(modes, dict) or not modes:
            raise ModelConfigError(f"Model `{model_code}` must define modes")

        pricing = {}
        for mode, mode_payload in modes.items():
            if not isinstance(mode_payload, dict):
                raise ModelConfigError(f"Model `{model_code}` mode `{mode}` must be a mapping")
            cost = int(mode_payload.get("cost", 0))
            if cost <= 0:
                raise ModelConfigError(
                    f"Model `{model_code}` mode `{mode}` must have positive cost"
                )
            pricing[str(mode)] = cost

        labels = payload.get("labels")
        if not isinstance(labels, list) or not labels:
            raise ModelConfigError(f"Model `{model_code}` must define labels")

        try:
            definitions.append(
                ModelDefinition(
                    model_code=str(model_code),
                    product_name=str(payload["product_name"]),
                    model_class=str(payload["model_class"]),
                    version=str(payload["version"]),
                    task_type=str(payload["task_type"]),
                    labels=[str(label) for label in labels],
                    pricing=pricing,
                )
            )
        except KeyError as exc:
            raise ModelConfigError(f"Model `{model_code}` is missing field `{exc.args[0]}`") from exc

    return definitions


def instantiate_classifier(class_path: str) -> BaseClassifier:
    module_name, _, class_name = class_path.rpartition(".")
    if not module_name or not class_name:
        raise ModelConfigError(f"Invalid model_class path: {class_path}")
    try:
        module = import_module(module_name)
        classifier_cls = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        raise ModelConfigError(f"Cannot import model_class `{class_path}`") from exc
    classifier = classifier_cls()
    if not isinstance(classifier, BaseClassifier):
        raise ModelConfigError(f"`{class_path}` does not implement BaseClassifier")
    return classifier
