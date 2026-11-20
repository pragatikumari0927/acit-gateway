"""ACIT Gateway — FastAPI application entry point."""

import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from src.api.dependencies import get_audit, get_catalog, get_idempotency, get_vault
from src.api.routes import audit as audit_routes
from src.api.routes import catalog as catalog_routes
from src.api.routes import checkout as checkout_routes
from src.api.routes import mandates as mandate_routes
from src.config import settings
from src.services.audit import AuditLogger
from src.services.catalog import CatalogService
from src.services.idempotency import IdempotencyStore
from src.services.vault import Vault
from src.services.webhook_apply import apply_verified_event, event_idempotency_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting ACIT Gateway on port 8000")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Chaos enabled: {settings.CHAOS_ENABLED}")
    print(f"MCP enabled: {settings.MCP_ENABLED}")
    # Initialize SQLModel tables (idempotent)
    from sqlmodel import SQLModel

    from src.api.dependencies import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()
    print("Shutting down ACIT Gateway")


# --- Razorpay Webhook Verification (native HMAC-SHA256) ---


def verify_razorpay_webhook_signature(body: str | bytes, signature: str, secret: str) -> bool:
    """Verify Razorpay webhook HMAC-SHA256 over the raw request body."""
    key = secret.encode("utf-8")
    msg = body if isinstance(body, bytes) else body.encode("utf-8")
    generated_signature = hmac.new(key=key, msg=msg, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_signature, signature)


# --- MCP Models ---


class MCPRequest(BaseModel):
    """MCP JSON-RPC request."""

    jsonrpc: str = "2.0"
    id: int | str | None = None
    method: str
    params: dict[str, Any] | None = None


class MCPResponse(BaseModel):
    """MCP JSON-RPC response."""

    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


# --- MCP Tools ---


class ListCatalogItemsArgs(BaseModel):
    """Arguments accepted by the `list_catalog_items` MCP tool."""

    merchant_id: str = Field(min_length=1)


def mcp_list_catalog_items(catalog: CatalogService, merchant_id: str) -> list[dict[str, Any]]:
    """Return a merchant's Catalog items. Raises KeyError for an unknown merchant."""
    return [item.model_dump() for item in catalog.get_catalog(merchant_id).items]


# --- MCP Router ---


def create_mcp_app() -> FastAPI:
    """Create MCP sub-application."""
    mcp_app = FastAPI(title="ACIT MCP Server", version="1.0.0")

    @mcp_app.post("/")
    async def mcp_endpoint(
        request: MCPRequest,
        catalog: CatalogService = Depends(get_catalog),
    ) -> MCPResponse:
        """Handle MCP JSON-RPC requests."""
        if request.method == "initialize":
            return MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "acit-gateway", "version": "1.0.0"},
                },
            )

        if request.method == "tools/list":
            return MCPResponse(
                id=request.id,
                result={
                    "tools": [
                        {
                            "name": "list_catalog_items",
                            "description": "List available catalog items for a merchant",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "merchant_id": {
                                        "type": "string",
                                        "description": "Merchant whose Catalog to list",
                                    }
                                },
                                "required": ["merchant_id"],
                            },
                        }
                    ]
                },
            )

        if request.method == "tools/call":
            tool_name = request.params.get("name") if request.params else None
            args = request.params.get("arguments", {}) if request.params else {}

            if tool_name == "list_catalog_items":
                try:
                    tool_args = ListCatalogItemsArgs.model_validate(args)
                except ValidationError:
                    return MCPResponse(
                        id=request.id,
                        error={"code": -32602, "message": "merchant_id is required"},
                    )
                try:
                    items = mcp_list_catalog_items(catalog, tool_args.merchant_id)
                except KeyError:
                    return MCPResponse(
                        id=request.id,
                        error={"code": -32602, "message": "merchant_not_found"},
                    )
                return MCPResponse(
                    id=request.id,
                    result={"content": [{"type": "text", "text": json.dumps(items)}]},
                )

            return MCPResponse(
                id=request.id,
                error={"code": -32601, "message": f"Unknown tool: {tool_name}"},
            )

        return MCPResponse(
            id=request.id,
            error={"code": -32601, "message": f"Method not found: {request.method}"},
        )

    @mcp_app.get("/")
    async def mcp_info():
        """MCP server info endpoint."""
        return {
            "name": "acit-gateway",
            "version": "1.0.0",
            "protocol": "MCP 2024-11-05",
            "transport": "HTTP",
        }

    return mcp_app


app = FastAPI(
    title="ACIT Gateway",
    description="Test-mode agentic payment bridge for Razorpay Buildathon",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests."""
    import time

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "acit-gateway"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ACIT Gateway",
        "description": "Test-mode agentic payment bridge",
        "version": "1.0.0",
        "docs": "/docs",
    }


# --- Webhook Handler ---


@app.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None, alias="X-Razorpay-Signature"),
    store: IdempotencyStore = Depends(get_idempotency),
    vault: Vault = Depends(get_vault),
    audit: AuditLogger = Depends(get_audit),
) -> Response:
    """Verify HMAC, claim the event, then apply Mandate + Audit (persist-then-apply)."""
    body = await request.body()

    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    try:
        if not verify_razorpay_webhook_signature(
            body=body,
            signature=x_razorpay_signature,
            secret=settings.RAZORPAY_WEBHOOK_SECRET,
        ):
            raise ValueError("Signature mismatch")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Response(
            content='{"status": "error", "reason": "malformed_json"}',
            media_type="application/json",
        )
    if not isinstance(payload, dict):
        return Response(
            content='{"status": "error", "reason": "malformed_json"}',
            media_type="application/json",
        )

    event_id = event_idempotency_key(payload)
    if not await store.mark(event_id):
        return Response(
            content='{"status": "already_processed"}',
            media_type="application/json",
        )

    result = await apply_verified_event(
        vault=vault,
        audit=audit,
        payload=payload,
        event_id=event_id,
    )
    return Response(content=json.dumps(result), media_type="application/json")


app.include_router(catalog_routes.router, prefix="/v1")
app.include_router(mandate_routes.router, prefix="/v1")
app.include_router(checkout_routes.router, prefix="/v1")
app.include_router(audit_routes.router, prefix="/v1")


# Mount MCP if enabled
if settings.MCP_ENABLED:
    mcp_app = create_mcp_app()
    app.mount("/mcp", mcp_app)
    print("MCP server mounted at /mcp")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )