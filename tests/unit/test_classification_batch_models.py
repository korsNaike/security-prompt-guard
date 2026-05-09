from app.domain.classifications.entities import ClassificationStatus
from app.infrastructure.db.models import ClassificationBatchModel


def test_classification_batch_defaults() -> None:
    batch = ClassificationBatchModel(
        user_id="00000000-0000-0000-0000-000000000001",
        total_requests=3,
    )

    assert batch.status == ClassificationStatus.PENDING.value
    assert batch.completed_requests == 0
    assert batch.failed_requests == 0
    assert batch.estimated_cost == 0
    assert batch.final_cost == 0
    assert batch.created_at is not None
