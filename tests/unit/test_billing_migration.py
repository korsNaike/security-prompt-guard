from pathlib import Path


def test_billing_migration_contains_required_tables() -> None:
    migration = Path("alembic/versions/20260509_0002_create_billing_domain.py")

    content = migration.read_text()

    assert 'create_table("billing_transactions"' in content
    assert 'create_table("promo_codes"' in content
    assert 'create_table("promo_code_activations"' in content
    assert 'create_table("loyalty_tiers"' in content
    assert 'create_table("loyalty_tier_history"' in content
    assert 'add_column("users"' in content
    assert "idempotency_key" in content
