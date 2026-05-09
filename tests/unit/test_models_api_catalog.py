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
