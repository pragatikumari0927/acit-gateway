"""The default Catalog path must resolve in every environment we ship.

The container copies neither `tests/` nor a usable `data/`, so the repo-root
seed is what keeps `docker compose up` serving a Catalog.
"""

from __future__ import annotations

from pathlib import Path

from src.api.dependencies import _default_catalog_file
from src.services.catalog import CatalogService

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_default_catalog_file_exists():
    assert Path(_default_catalog_file()).is_file()


def test_repo_root_seed_is_a_loadable_catalog():
    """The seed baked into the image must parse and expose the demo merchant."""
    seed = REPO_ROOT / "catalogs.json"
    assert seed.is_file()

    catalog = CatalogService(str(seed))
    response = catalog.get_catalog("m_test")

    assert response.merchant_id == "m_test"
    assert response.items


def test_local_runs_still_prefer_the_test_fixture():
    """The seed is a fallback; adding it must not change local resolution."""
    assert Path(_default_catalog_file()) == REPO_ROOT / "tests" / "fixtures" / "catalogs.json"


def test_resolves_root_seed_when_earlier_candidates_are_absent(tmp_path, monkeypatch):
    """The container layout: no tests/ directory and an empty bind-mounted data/."""
    (tmp_path / "data").mkdir()
    seed = tmp_path / "catalogs.json"
    seed.write_text((REPO_ROOT / "catalogs.json").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr("src.api.dependencies._REPO_ROOT", tmp_path)

    assert Path(_default_catalog_file()) == seed
    assert CatalogService(_default_catalog_file()).get_catalog("m_test").items
