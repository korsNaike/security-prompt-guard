from app.infrastructure.db.models import AuditLogModel


def test_audit_log_model_defaults() -> None:
    log = AuditLogModel(
        actor_user_id="00000000-0000-0000-0000-000000000001",
        action="auth.login",
        entity_type="user",
        entity_id="00000000-0000-0000-0000-000000000001",
        event_metadata={"source": "test"},
    )

    assert log.id is not None
    assert log.created_at is not None
    assert log.action == "auth.login"
    assert log.event_metadata == {"source": "test"}
