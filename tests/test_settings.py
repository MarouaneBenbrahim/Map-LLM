def test_settings_import_and_default_instantiation():
    # Should not raise (e.g. torch optional dependency)
    from config.settings import PowerGridSettings

    settings = PowerGridSettings()
    assert settings.performance_config["enable_gpu"] in (True, False)

