def pytest_configure(config):
    # Installed, the plugin registers itself by entry point; a bare checkout needs it loaded here.
    if not config.pluginmanager.has_plugin("printgate"):
        config.pluginmanager.import_plugin("printgate.scad.pytest_plugin")
