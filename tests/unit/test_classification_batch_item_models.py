from uuid import uuid4

from app.domain.classifications.entities import ClassificationStatus
from app.infrastructure.db.models import ClassificationBatchItemModel


def test_classification_batch_item_defaults() -> None:
    item = ClassificationBatchItemModel(
        batch_id="00000000-0000-0000-0000-000000000001",
        classification_request_id="00000000-0000-0000-0000-000000000002",
        item_index=0,
    )

    assert item.status == ClassificationStatus.PENDING.value
    assert item.estimated_cost == 0
    assert item.final_cost is None
    assert item.created_at is not None


def test_classification_batch_item_tracks_costs() -> None:
    item = ClassificationBatchItemModel(
        batch_id=uuid4(),
        classification_request_id=uuid4(),
        item_index=0,
        estimated_cost=7,
    )

    assert item.estimated_cost == 7
    assert item.final_cost is None
