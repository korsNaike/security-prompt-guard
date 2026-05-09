from pathlib import Path


def test_classification_batch_migration_contains_required_schema() -> None:
    migration = Path("alembic/versions/20260509_0004_create_classification_batches.py")

    content = migration.read_text()

    assert '"classification_batches"' in content
    assert '"classification_requests", sa.Column("batch_id", sa.Uuid(), nullable=True)' in content
    assert "fk_classification_requests_batch_id" in content
