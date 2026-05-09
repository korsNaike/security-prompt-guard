import pytest

from app.api.v1.models import get_model, list_models
from app.application.models.catalog_service import to_model_info


def test_to_model_info_maps_db_pricing_to_api_schema() -> None:
    pricing = [
        type("Pricing", (), {"mode": "basic", "cost": 3, "is_active": True})(),
        type("Pricing", (), {"mode": "standard", "cost": 7, "is_active": True})(),
        type("Pricing", (), {"mode": "legacy", "cost": 99, "is_active": False})(),
    ]
    model = type(
        "Model",
        (),
        {
            "model_code": "prompt_guard",
            "product_name": "SecurePrompt Guard",
            "model_name": "PromptGuardClassifier",
            "model_version": "0.1.0",
            "task_type": "prompt_security_classification",
            "labels": ["safe"],
            "pricing": pricing,
        },
    )()

    info = to_model_info(model)

    assert info.model_code == "prompt_guard"
    assert info.pricing == {"basic": 3, "standard": 7}
    assert info.supported_modes == ["basic", "standard"]


class FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@pytest.mark.anyio
async def test_list_and_detail_models_use_same_catalog_source(monkeypatch) -> None:
    pricing = [type("Pricing", (), {"mode": "standard", "cost": 7, "is_active": True})()]
    model = type(
        "Model",
        (),
        {
            "model_code": "prompt_guard",
            "product_name": "SecurePrompt Guard",
            "model_name": "PromptGuardClassifier",
            "model_version": "0.1.0",
            "task_type": "prompt_security_classification",
            "labels": ["safe"],
            "pricing": pricing,
        },
    )()

    async def fake_catalog_models(session):
        return [model]

    monkeypatch.setattr("app.api.v1.models._get_catalog_models", fake_catalog_models)

    listed = await list_models(FakeSession())
    detailed = await get_model("prompt_guard", FakeSession())

    assert listed.items[0].model_name == "PromptGuardClassifier"
    assert detailed.model_name == "PromptGuardClassifier"
