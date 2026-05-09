from app.domain.classifications.entities import ClassificationStatus
from app.infrastructure.db.models import ClassificationRequestModel, ClassificationResultModel


def test_classification_request_defaults() -> None:
    request = ClassificationRequestModel(
        user_id="00000000-0000-0000-0000-000000000001",
        model_code="prompt_guard",
        mode="standard",
        input_text="test",
        input_hash="hash",
        estimated_cost=7,
    )

    assert request.status == ClassificationStatus.PENDING.value
    assert request.created_at is not None


def test_classification_result_defaults() -> None:
    result = ClassificationResultModel(
        request_id="00000000-0000-0000-0000-000000000002",
        label="safe",
        confidence=0.91,
        model_code="prompt_guard",
        model_version="baseline-rules-v1",
    )

    assert result.id is not None
    assert result.created_at is not None
