import pytest

from app.core.exceptions import ModelNotFoundError, UnsupportedModeError
from app.infrastructure.ml.loader import build_model_registry


def test_registry_lists_configured_models() -> None:
    registry = build_model_registry()

    model_codes = {model.model_code for model in registry.list_models()}

    assert model_codes == {"prompt_guard"}


def test_registry_returns_pricing_by_mode() -> None:
    registry = build_model_registry()

    assert registry.get_cost("prompt_guard", "standard") == 7
    assert registry.get_cost("prompt_guard", "basic") == 3


def test_registry_rejects_unknown_model() -> None:
    registry = build_model_registry()

    with pytest.raises(ModelNotFoundError):
        registry.get("missing")


def test_registry_rejects_unsupported_mode() -> None:
    registry = build_model_registry()

    with pytest.raises(UnsupportedModeError):
        registry.get_cost("prompt_guard", "enterprise")
