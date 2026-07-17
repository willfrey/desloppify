"""Packaging metadata invariants for optional dependency extras."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


def _optional_dependencies() -> dict[str, list[str]]:
    pyproject_path = Path(__file__).resolve().parents[3] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    optional = project.get("optional-dependencies", {})
    assert isinstance(optional, dict), "project.optional-dependencies must be a table"
    return optional


def _package_names(specs: list[str]) -> set[str]:
    names: set[str] = set()
    for spec in specs:
        name = re.split(r"[<>=!~;\s\[]", str(spec), maxsplit=1)[0].strip().lower()
        if name:
            names.add(name)
    return names


def test_full_extra_matches_union_of_other_extras() -> None:
    optional = _optional_dependencies()
    full_specs = optional.get("full")
    assert isinstance(full_specs, list), "optional extra 'full' must be a list"

    other_extra_names = [name for name in optional if name != "full"]
    expected = sorted(
        {
            str(spec)
            for extra_name in other_extra_names
            for spec in optional.get(extra_name, [])
        }
    )
    actual = sorted(str(spec) for spec in full_specs)
    assert actual == expected


def test_treesitter_extra_declares_runtime_and_language_pack() -> None:
    optional = _optional_dependencies()
    treesitter_specs = optional.get("treesitter")
    assert isinstance(treesitter_specs, list), "optional extra 'treesitter' must be a list"
    package_names = _package_names(treesitter_specs)
    assert "tree-sitter" in package_names
    assert "tree-sitter-language-pack" in package_names


def test_treesitter_language_pack_floor_clears_broken_releases() -> None:
    """The floor must be >= 1.12.5 and must not re-cap below it.

    History: PR #605 capped ``<1.8`` because 1.8.0 returned a ``builtins.Language``
    that crashed the cohesion phase (``TypeError: __new__() argument 1 must be
    tree_sitter.Language``). But on Python 3.14 the ``<1.8`` resolution lands on
    1.6.3, whose cp314 wheel ships no importable ``tree_sitter_language_pack``
    package at all — so the cap silently disabled *every* tree-sitter grammar
    (Go, Rust, Bash, TypeScript, …) on 3.14, since each detector swallows the
    init failure and reports no findings. 1.12.5 restores a real
    ``tree_sitter.Language`` (the #605 crash no longer reproduces) and a working
    3.14 wheel. The floor pins that; the assertion fails if anyone reinstates a
    ``<`` cap at or below the known-broken range.
    """
    optional = _optional_dependencies()
    for extra in ("treesitter", "full"):
        specs = optional.get(extra)
        assert isinstance(specs, list), f"optional extra {extra!r} must be a list"
        pack = next(
            (s for s in specs if str(s).startswith("tree-sitter-language-pack")), None
        )
        assert pack is not None, f"{extra!r} must declare tree-sitter-language-pack"
        floor = re.search(r">=\s*([0-9][0-9.]*)", str(pack))
        assert floor is not None, f"{extra!r} pack spec must carry a >= floor: {pack!r}"
        assert _version_tuple(floor.group(1)) >= (1, 12, 5), (
            f"{extra!r} floor {floor.group(1)} is below 1.12.5, which is the first "
            "release that is both #605-safe and has a working Python 3.14 wheel"
        )
        upper = re.search(r"<\s*([0-9][0-9.]*)", str(pack))
        if upper is not None:
            assert _version_tuple(upper.group(1)) > (1, 12, 5), (
                f"{extra!r} re-caps tree-sitter-language-pack at {upper.group(1)}, "
                "at or below the broken range — see this test's docstring"
            )


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))
