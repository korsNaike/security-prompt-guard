from app.infrastructure.db.models import MLModelModel, ModelPricingModel


def test_ml_model_defaults() -> None:
    model = MLModelModel(
        model_code="prompt_guard",
        product_name="SecurePrompt Guard",
        model_name="PromptGuardClassifier",
        model_version="0.1.0",
        task_type="prompt_security_classification",
        labels=["safe", "prompt_injection"],
    )

    assert model.is_active is True
    assert model.created_at is not None


def test_model_pricing_defaults() -> None:
    pricing = ModelPricingModel(
        model_code="prompt_guard",
        mode="standard",
        cost=7,
    )

    assert pricing.is_active is True
    assert pricing.created_at is not None
