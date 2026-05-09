from uuid import uuid4

from app.application.classifications.use_cases import (
    ClassificationBatchSizeError,
    ClassificationService,
)


class FakeRegistry:
    def get_cost(self, model_code: str, mode: str) -> int:
        return 7


class FakeRepository:
    def __init__(self) -> None:
        self.batch_id = uuid4()
        self.requests = []

    async def create_batch(self, **kwargs):
        return type(
            "Batch",
            (),
            {
                "id": self.batch_id,
                "status": "pending",
                "total_requests": kwargs["total_requests"],
                "estimated_cost": kwargs["estimated_cost"],
            },
        )()

    async def create_request(self, **kwargs):
        request = type(
            "Request",
            (),
            {
                "id": uuid4(),
                "model_code": kwargs["model_code"],
                "mode": kwargs["mode"],
                "estimated_cost": kwargs["estimated_cost"],
            },
        )()
        self.requests.append((request, kwargs))
        return request

    async def create_batch_item(self, **kwargs):
        return type("BatchItem", (), kwargs)()

    async def set_celery_task_id(self, *, request_id, celery_task_id: str) -> None:
        return None


class FakeBillingRepository:
    def __init__(self) -> None:
        self.reservations = []

    async def reserve_credits(self, **kwargs):
        self.reservations.append(kwargs)


async def test_create_batch_creates_children_reserves_and_enqueues() -> None:
    repository = FakeRepository()
    billing_repository = FakeBillingRepository()
    sent = []
    service = ClassificationService(
        repository=repository,
        billing_repository=billing_repository,
        model_registry=FakeRegistry(),
        task_sender=lambda request_id: sent.append(request_id) or f"task-{len(sent)}",
    )

    result = await service.create_batch(
        user_id=uuid4(),
        model_code="prompt_guard",
        mode="standard",
        items=["one", "two"],
    )

    assert result["batch"].estimated_cost == 14
    assert len(result["requests"]) == 2
    assert len(billing_repository.reservations) == 2
    assert [request.id for request in result["requests"]] == sent


async def test_create_batch_rejects_empty_payload() -> None:
    service = ClassificationService(
        repository=FakeRepository(),
        billing_repository=FakeBillingRepository(),
        model_registry=FakeRegistry(),
    )

    try:
        await service.create_batch(
            user_id=uuid4(),
            model_code="prompt_guard",
            mode="standard",
            items=[],
        )
    except ClassificationBatchSizeError:
        return

    raise AssertionError("Expected ClassificationBatchSizeError")


async def test_create_batch_accepts_100_items() -> None:
    repository = FakeRepository()
    billing_repository = FakeBillingRepository()
    service = ClassificationService(
        repository=repository,
        billing_repository=billing_repository,
        model_registry=FakeRegistry(),
    )

    result = await service.create_batch(
        user_id=uuid4(),
        model_code="prompt_guard",
        mode="standard",
        items=[f"text {index}" for index in range(100)],
    )

    assert result["batch"].total_requests == 100
    assert len(result["requests"]) == 100
    assert len(billing_repository.reservations) == 100
