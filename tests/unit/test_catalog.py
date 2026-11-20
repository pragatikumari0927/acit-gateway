"""Unit tests for C2 Semantic Catalog (TDD vertical slices).

Tests hit only public seams: models + CatalogService.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.catalog import (
    CatalogItem,
    CatalogResponse,
    DiscountBounds,
)
from src.services.catalog import CatalogService


def test_discount_bounds_valid_construction():
    b = DiscountBounds(min_percent=0, max_percent=15)
    assert b.min_percent == 0
    assert b.max_percent == 15


def test_discount_bounds_validation_rejects_bad_range():
    with pytest.raises(ValidationError):
        DiscountBounds(min_percent=-1, max_percent=10)
    with pytest.raises(ValidationError):
        DiscountBounds(min_percent=5, max_percent=101)


def test_catalog_item_construction():
    bounds = DiscountBounds(min_percent=0, max_percent=10)
    item = CatalogItem(
        sku="SKU-001",
        name="Widget",
        description="A useful widget",
        unit_amount_paise=19900,
        inventory=42,
        discount_bounds=bounds,
        categories=["gadget", "new"],
    )
    assert item.sku == "SKU-001"
    assert item.unit_amount_paise == 19900
    assert item.discount_bounds.max_percent == 10
    assert "gadget" in item.categories


def test_catalog_item_validation_rejects_bad_price():
    bounds = DiscountBounds(min_percent=0, max_percent=5)
    with pytest.raises(ValidationError):
        CatalogItem(
            sku="BAD",
            name="Bad",
            unit_amount_paise=-1,
            inventory=1,
            discount_bounds=bounds,
        )


def test_catalog_response_construction():
    bounds = DiscountBounds(min_percent=0, max_percent=10)
    item = CatalogItem(
        sku="SKU-001",
        name="Widget",
        description="",
        unit_amount_paise=100,
        inventory=10,
        discount_bounds=bounds,
    )
    resp = CatalogResponse(
        merchant_id="m_test",
        merchant_name="Test Merchant",
        items=[item],
        updated_at="2026-09-02T00:00:00Z",
    )
    assert resp.merchant_id == "m_test"
    assert len(resp.items) == 1
    assert resp.items[0].sku == "SKU-001"


# --- C2 service seams (red-green next vertical slice) ---

def test_catalog_service_injects_catalog_file(tmp_path):
    # Use the committed fixture path (service must accept it)
    svc = CatalogService("tests/fixtures/catalogs.json")
    assert svc.catalog_file.endswith("catalogs.json")


def test_get_catalog_happy_path():
    svc = CatalogService("tests/fixtures/catalogs.json")
    resp = svc.get_catalog("m_test")
    assert isinstance(resp, CatalogResponse)
    assert resp.merchant_id == "m_test"
    assert resp.merchant_name == "Test Merchant"
    assert len(resp.items) >= 1
    assert any(i.sku == "SKU-001" for i in resp.items)


def test_get_catalog_unknown_merchant_raises():
    svc = CatalogService("tests/fixtures/catalogs.json")
    with pytest.raises(KeyError):
        svc.get_catalog("does_not_exist")


def test_get_item_happy():
    svc = CatalogService("tests/fixtures/catalogs.json")
    item = svc.get_item("m_test", "SKU-001")
    assert isinstance(item, CatalogItem)
    assert item.sku == "SKU-001"
    assert item.unit_amount_paise == 19900


def test_get_item_missing_sku_raises():
    svc = CatalogService("tests/fixtures/catalogs.json")
    with pytest.raises(KeyError):
        svc.get_item("m_test", "NOPE")


def test_search_matches_name_or_category():
    svc = CatalogService("tests/fixtures/catalogs.json")
    results = svc.search("m_test", "widget")
    assert len(results) >= 1
    assert results[0].sku == "SKU-001"

    results2 = svc.search("m_test", "pro")
    assert any(r.sku == "SKU-002" for r in results2)


def test_search_no_match_returns_empty():
    svc = CatalogService("tests/fixtures/catalogs.json")
    results = svc.search("m_test", "nonexistent-xyz")
    assert results == []
