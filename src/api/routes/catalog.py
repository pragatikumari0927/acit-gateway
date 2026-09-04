"""Catalog read routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_catalog
from src.models.catalog import CatalogItem, CatalogResponse
from src.services.catalog import CatalogService

router = APIRouter()


@router.get("/catalog", response_model=CatalogResponse)
async def read_catalog(
    merchant_id: str = Query(...),
    catalog: CatalogService = Depends(get_catalog),
) -> CatalogResponse:
    """Return a merchant's Catalog."""
    try:
        return catalog.get_catalog(merchant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="merchant_not_found") from exc


@router.get("/catalog/{sku}", response_model=CatalogItem)
async def read_catalog_item(
    sku: str,
    merchant_id: str = Query(...),
    catalog: CatalogService = Depends(get_catalog),
) -> CatalogItem:
    """Return one CatalogItem by SKU."""
    try:
        return catalog.get_item(merchant_id, sku)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="sku_not_found") from exc
