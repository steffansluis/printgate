import pytest

from printgate import plugins
from printgate.reporters.text import TextReporter


def test_builtin_loads_without_installing():
    assert plugins.load("printgate.reporters", "text") is TextReporter


def test_unknown_name_lists_what_exists():
    with pytest.raises(KeyError, match="markdown"):
        plugins.load("printgate.reporters", "nonesuch")
