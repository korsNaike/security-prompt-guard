from pathlib import Path


def test_classification_migration_contains_required_tables() -> None:
    migration = Path("alembic/versions/20260509_0003_create_classification_requests.py")

    content = migration.read_text()

    assert 'create_table(\n        "classification_requests"' in content
    assert 'create_table(\n        "classification_results"' in content
    assert "fk_billing_transactions_classification_request_id" in content
    assert 'sa.Column("metadata", sa.JSON(), nullable=True)' in content
