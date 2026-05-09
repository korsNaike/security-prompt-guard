def test_app_package_imports() -> None:
    import app

    assert app.__doc__ == "SecurePrompt Guard application package."
