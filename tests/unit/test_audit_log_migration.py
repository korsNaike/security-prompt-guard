from pathlib import Path


def test_audit_log_migration_creates_required_table() -> None:
    content = Path("alembic/versions/20260509_0007_create_audit_logs.py").read_text()

    assert '"audit_logs"' in content
    assert "actor_user_id" in content
    assert "action" in content
    assert "entity_type" in content
    assert "metadata" in content
