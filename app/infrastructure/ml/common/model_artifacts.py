from dataclasses import dataclass


@dataclass(frozen=True)
class TextClassificationArtifact:
    model_code: str
    product_name: str
    model_name: str
    model_id_or_path: str
    model_version: str
    task_type: str
    supported_modes: list[str]
    labels: list[str]
    label_mapping: dict[str, str]
    revision: str | None = None
    default_risk_level: str = "medium"
    default_recommended_action: str = "review"

    def validate(self) -> None:
        required_strings = {
            "model_code": self.model_code,
            "product_name": self.product_name,
            "model_name": self.model_name,
            "model_id_or_path": self.model_id_or_path,
            "model_version": self.model_version,
            "task_type": self.task_type,
        }
        missing = [field for field, value in required_strings.items() if not value.strip()]
        if missing:
            raise ValueError(f"Missing artifact fields: {', '.join(missing)}")
        if not self.supported_modes:
            raise ValueError("supported_modes must not be empty")
        if not self.labels:
            raise ValueError("labels must not be empty")
        if not self.label_mapping:
            raise ValueError("label_mapping must not be empty")
