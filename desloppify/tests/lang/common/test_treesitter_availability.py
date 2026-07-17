"""Availability warnings for the tree-sitter language pack.

Unlike ``test_treesitter.py`` these tests must run without the optional
package installed — they cover exactly the paths taken when it is absent
or broken.
"""

from __future__ import annotations

import importlib.metadata

import desloppify.languages._framework.treesitter as ts_mod


def test_broken_pack_warning_quiet_when_pack_absent(monkeypatch, capsys):
    """No distribution metadata means an intentional minimal install: stay quiet."""

    def _not_found(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", _not_found)
    ts_mod._warn_if_pack_installed_but_broken(ImportError("nope"))
    assert capsys.readouterr().err == ""


def test_broken_pack_warning_fires_when_pack_installed(monkeypatch, capsys):
    """Metadata present plus an import failure is a broken install: warn loudly."""
    monkeypatch.setattr(importlib.metadata, "version", lambda _name: "1.6.3")
    ts_mod._warn_if_pack_installed_but_broken(ImportError("no importable package"))
    err = capsys.readouterr().err
    assert "1.6.3" in err
    assert "no findings" in err
