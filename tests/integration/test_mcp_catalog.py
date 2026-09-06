"""Integration tests for the MCP catalog tool (H3).

The MCP sub-app must serve the same Catalog as `GET /v1/catalog`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
# A SKU identifier, e.g. SKU001 or SKU-001. Prose mentioning "SKU" is fine.
SKU_LITERAL = re.compile(r"SKU[-_]?\d")


def _mcp_client() -> TestClient:
    from src.main import create_mcp_app

    return TestClient(create_mcp_app())


def _call_tool(client: TestClient, arguments: dict) -> dict:
    response = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "list_catalog_items", "arguments": arguments},
        },
    )
    assert response.status_code == 200
    return response.json()


def _tool_items(body: dict) -> list[dict]:
    assert body.get("error") is None
    return json.loads(body["result"]["content"][0]["text"])


def test_mcp_catalog_matches_v1_catalog_route():
    """Same merchant through MCP and the REST route returns the same items."""
    from src.main import app

    mcp_items = _tool_items(_call_tool(_mcp_client(), {"merchant_id": "m_test"}))

    rest = TestClient(app).get("/v1/catalog", params={"merchant_id": "m_test"})
    assert rest.status_code == 200

    assert mcp_items == rest.json()["items"]


def test_mcp_catalog_is_merchant_scoped():
    """A second merchant returns its own SKUs, not a fixed in-file list."""
    client = _mcp_client()

    first = _tool_items(_call_tool(client, {"merchant_id": "m_test"}))
    second = _tool_items(_call_tool(client, {"merchant_id": "m_other"}))

    assert [i["sku"] for i in first] != [i["sku"] for i in second]
    assert second == [
        {
            "sku": "SKU-999",
            "name": "Thing",
            "description": "",
            "unit_amount_paise": 100,
            "inventory": 100,
            "discount_bounds": {"min_percent": 0, "max_percent": 0},
            "categories": [],
        }
    ]


def test_mcp_catalog_unknown_merchant_is_jsonrpc_error():
    """An unknown merchant is a coded error, never placeholder items."""
    body = _call_tool(_mcp_client(), {"merchant_id": "m_nope"})

    assert body["result"] is None
    assert body["error"]["code"] == -32602
    assert body["error"]["message"] == "merchant_not_found"


def test_mcp_catalog_missing_merchant_id_is_jsonrpc_error():
    """merchant_id is required; omitting it is invalid params."""
    body = _call_tool(_mcp_client(), {})

    assert body["result"] is None
    assert body["error"]["code"] == -32602
    assert body["error"]["message"] == "merchant_id is required"


def test_mcp_tools_list_requires_merchant_id():
    """The advertised schema matches the handler contract."""
    response = _mcp_client().post("/", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    schema = next(t for t in tools if t["name"] == "list_catalog_items")["inputSchema"]
    assert schema["required"] == ["merchant_id"]


def test_no_hardcoded_skus_in_src():
    """Catalog data lives in the Catalog file, never inline in src/."""
    offenders = [
        path.relative_to(SRC_DIR).as_posix()
        for path in SRC_DIR.rglob("*.py")
        if SKU_LITERAL.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
