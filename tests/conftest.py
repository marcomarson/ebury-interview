def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "acceptance: end-to-end acceptance checks that require a populated warehouse "
        "(run after the pipeline; excluded from the default unit/integration run)",
    )
