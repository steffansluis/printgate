import pytest

from printgate import config

PRINTER = '[printers.mk]\nfirmware = "klipper"\nslicer = "prusaslicer"\nslicer_config = "p.ini"\n'


def test_nothing_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("PRINTGATE_CONFIG", raising=False)
    assert config.load(cwd=tmp_path).printers == ()


def test_printgate_toml_beats_pyproject(tmp_path, monkeypatch):
    monkeypatch.delenv("PRINTGATE_CONFIG", raising=False)
    (tmp_path / "pyproject.toml").write_text("[tool.printgate.printers.other]\n")
    assert config.load(cwd=tmp_path).printers[0].name == "other"
    (tmp_path / "printgate.toml").write_text(PRINTER)
    assert config.load(cwd=tmp_path).printers[0].name == "mk"


def test_env_points_at_a_file_and_paths_resolve_beside_it(tmp_path, monkeypatch):
    (tmp_path / "ci").mkdir()
    (tmp_path / "ci" / "pg.toml").write_text(PRINTER)
    monkeypatch.setenv("PRINTGATE_CONFIG", str(tmp_path / "ci" / "pg.toml"))
    p = config.load(cwd=tmp_path).printer("mk")
    assert p.slicer_config == tmp_path / "ci" / "p.ini"
    assert p.profile.firmware == "klipper"


def test_env_narrows_the_printers(tmp_path, monkeypatch):
    (tmp_path / "printgate.toml").write_text(PRINTER + "[printers.big]\n")
    monkeypatch.delenv("PRINTGATE_CONFIG", raising=False)
    monkeypatch.setenv("PRINTGATE_PRINTERS", "big")
    assert [p.name for p in config.load(cwd=tmp_path).printers] == ["big"]
    monkeypatch.setenv("PRINTGATE_PRINTERS", "nonesuch")
    with pytest.raises(KeyError, match="mk, big"):
        config.load(cwd=tmp_path)


@pytest.mark.parametrize("text, match", [
    ("[printers.mk]\nbed_size = 1\n", "bed_size"),
    ("printer = 1\n", "unknown keys printer"),
    ('[printers.mk]\nfirmware = "nonesuch"\n', "unknown firmware"),
])
def test_mistakes_are_named(tmp_path, monkeypatch, text, match):
    monkeypatch.delenv("PRINTGATE_CONFIG", raising=False)
    (tmp_path / "printgate.toml").write_text(text)
    with pytest.raises(ValueError, match=match):
        config.load(cwd=tmp_path)


def test_review_context(tmp_path, monkeypatch):
    monkeypatch.delenv("PRINTGATE_CONFIG", raising=False)
    (tmp_path / "printgate.toml").write_text('[review]\ncontext = { mode = "assembly" }\n')
    assert config.load(cwd=tmp_path).context == {"mode": "assembly"}
