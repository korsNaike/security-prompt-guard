from pathlib import Path


def test_model_catalog_migration_contains_required_tables() -> None:
    content = Path(
        "alembic/versions/20260509_0005_create_model_catalog_and_batch_items.py"
    ).read_text()

    assert '"ml_models"' in content
    assert '"model_pricing"' in content
    assert '"classification_batch_items"' in content
