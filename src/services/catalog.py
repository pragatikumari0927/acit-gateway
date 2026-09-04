"""CatalogService for C2 Semantic Catalog.

Injected catalog_file (static JSON). No LLM. Uses CONTEXT vocabulary.
Public interface: get_catalog, get_item, search.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.models.catalog import CatalogItem, CatalogResponse, DiscountBounds


class CatalogService:
    """Semantic Catalog (C2). Agent-readable offers from merchant.

    catalog_file injected. Loads once at construction.
    """

    def __init__(self, catalog_file: str) -> None:
        self.catalog_file = str(catalog_file)
        raw = json.loads(Path(self.catalog_file).read_text(encoding="utf-8"))
        # Support both {"m_id": {...}} or {"merchants": {"m_id": ...}}
        if "merchants" in raw and isinstance(raw["merchants"], dict):
            self._merchants = raw["merchants"]
        else:
            self._merchants = raw

    def get_catalog(self, merchant_id: str) -> CatalogResponse:
        data = self._merchants.get(merchant_id)
        if data is None:
            raise KeyError(merchant_id)
        items = [
            CatalogItem(
                sku=i["sku"],
                name=i["name"],
                description=i.get("description", ""),
                unit_amount_paise=int(i["unit_amount_paise"]),
                inventory=int(i.get("inventory", 0)),
                discount_bounds=DiscountBounds(**i["discount_bounds"]),
                categories=i.get("categories", []),
            )
            for i in data.get("items", [])
        ]
        return CatalogResponse(
            merchant_id=data.get("merchant_id", merchant_id),
            merchant_name=data.get("merchant_name", ""),
            items=items,
            updated_at=data.get("updated_at", ""),
        )

    def get_item(self, merchant_id: str, sku: str) -> CatalogItem:
        cat = self.get_catalog(merchant_id)
        for it in cat.items:
            if it.sku == sku:
                return it
        raise KeyError(sku)

    def search(self, merchant_id: str, query: str) -> list[CatalogItem]:
        cat = self.get_catalog(merchant_id)
        if not query:
            return []
        q = query.lower()
        out: list[CatalogItem] = []
        for it in cat.items:
            hay = f"{it.name} {it.description} {' '.join(it.categories)}".lower()
            if q in hay:
                out.append(it)
        return out
