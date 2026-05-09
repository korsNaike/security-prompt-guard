from app.domain.ml.classifier_contracts import (
    BaseClassifier,
    ClassificationInput,
    ClassificationOutput,
)
from app.infrastructure.ml.prompt_guard.rules import classify_prompt_by_rules

ACTION_BY_LABEL = {
    "safe": "allow",
    "suspicious": "review",
    "prompt_injection": "block",
    "jailbreak": "block",
    "harmful": "block",
    "data_exfiltration": "block",
}

RISK_BY_LABEL = {
    "safe": "low",
    "suspicious": "medium",
    "prompt_injection": "high",
    "jailbreak": "high",
    "harmful": "high",
    "data_exfiltration": "critical",
}


class PromptGuardClassifier(BaseClassifier):
    model_code = "prompt_guard"
    product_name = "SecurePrompt Guard"
    model_name = "Rule-Based Prompt Guard Baseline"
    model_version = "0.1.0"
    task_type = "prompt_security_classification"
    supported_modes = ["basic", "standard", "advanced"]
    labels = ["safe", "prompt_injection", "jailbreak", "harmful", "data_exfiltration", "suspicious"]

    def predict(self, input_data: ClassificationInput) -> ClassificationOutput:
        label, confidence, explanation = classify_prompt_by_rules(input_data.text)
        return ClassificationOutput(
            label=label,
            confidence=confidence,
            risk_level=RISK_BY_LABEL[label],
            recommended_action=ACTION_BY_LABEL[label],
            explanation=explanation,
            raw_scores={label: confidence},
            metadata={"baseline": "rules", "mode": input_data.mode},
        )
