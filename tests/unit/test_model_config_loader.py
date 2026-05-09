from pathlib import Path

import pytest

from app.infrastructure.ml.config_loader import ModelConfigError, load_model_definitions


def test_load_model_definitions_from_yaml(tmp_path: Path) -> None:
    config = tmp_path / "models.yml"
    config.write_text(
        """
models:
  prompt_guard:
    product_name: SecurePrompt Guard
    model_class: app.infrastructure.ml.prompt_guard.classifier.PromptGuardClassifier
    model_name: Rule-Based Prompt Guard Baseline
    version: 0.1.0
    task_type: prompt_security_classification
    modes:
      standard:
        cost: 7
    labels: [safe, prompt_injection]
"""
    )

    definitions = load_model_definitions(config)

    assert definitions[0].model_code == "prompt_guard"
    assert definitions[0].model_name == "Rule-Based Prompt Guard Baseline"
    assert definitions[0].pricing == {"standard": 7}


def test_load_model_definitions_rejects_non_positive_cost(tmp_path: Path) -> None:
    config = tmp_path / "models.yml"
    config.write_text(
        """
models:
  broken:
    product_name: Broken
    model_class: app.infrastructure.ml.prompt_guard.classifier.PromptGuardClassifier
    version: 0.1.0
    task_type: prompt_security_classification
    modes:
      standard:
        cost: 0
    labels: [safe]
"""
    )

    with pytest.raises(ModelConfigError, match="positive cost"):
        load_model_definitions(config)
