from app.infrastructure.tasks.celery_app import celery_app


def test_celery_beat_schedule_contains_required_maintenance_tasks() -> None:
    schedule = celery_app.conf.beat_schedule

    assert "monthly-loyalty-recalculation" in schedule
    assert "deactivate-expired-promo-codes" in schedule
    assert "cleanup-stale-classification-requests" in schedule
