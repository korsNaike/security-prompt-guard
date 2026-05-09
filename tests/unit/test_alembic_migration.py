from pathlib import Path


def test_initial_migration_contains_users_and_balances() -> None:
    migration = Path("alembic/versions/20260509_0001_create_users_and_balances.py")

    content = migration.read_text()

    assert 'create_table("users"' in content
    assert 'create_table("user_balances"' in content
    assert "uq_user_balances_user_id" in content
