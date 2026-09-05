"""ACIT Gateway — FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import Any
import hmac
import hashlib

from fastapi import FastAPI, Request, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.routes import audit as audit_routes
from src.api.routes import catalog as catalog_routes
from src.api.routes import checkout as checkout_routes
from src.api.routes import mandates as mandate_routes
from src.config import settings


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


def verify_razorpay_webhook_signature(body: str, signature: str, secret: str) -> bool:
    """
    Verify Razorpay webhook signature using HMAC-SHA256.
    
    Implements the same logic as razorpay.utility.verify_webhook_signature
    without requiring pkg_resources.
    """
    key = secret.encode("utf-8")
    msg = body.encode("utf-8")
    
    dig = hmac.new(key=key, msg=msg, digestmod=hashlib.sha256)
    generated_signature = dig.hexdigest()
    
    # Use hmac.compare_digest for constant-time comparison (Python 3.3+)
    return hmac.compare_digest(generated_signature, signature)


# --- Idempotency store (in-memory for demo, could be Redis/SQLite) ---
_idempotency_keys: set[str] = set()


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


async def mcp_list_catalog_items(merchant_id: str | None = None) -> list[dict[str, Any]]:
    """List catalog items (placeholder for C5)."""
    # TODO: Implement actual catalog lookup via src/services/catalog.py
    return [
        {"sku": "SKU001", "name": "Test Product", "amount_paise": 1000, "currency": "INR"},
        {"sku": "SKU002", "name": "Another Product", "amount_paise": 2500, "currency": "INR"},
    ]


# --- MCP Router ---


def create_mcp_app() -> FastAPI:
    """Create MCP sub-application."""
    mcp_app = FastAPI(title="ACIT MCP Server", version="1.0.0")

    @mcp_app.post("/")
    async def mcp_endpoint(request: MCPRequest) -> MCPResponse:
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
                                        "description": "Optional merchant ID to filter by",
                                    }
                                },
                            },
                        }
                    ]
                },
            )

        if request.method == "tools/call":
            tool_name = request.params.get("name") if request.params else None
            args = request.params.get("arguments", {}) if request.params else {}

            if tool_name == "list_catalog_items":
                items = await mcp_list_catalog_items(args.get("merchant_id"))
                return MCPResponse(
                    id=request.id,
                    result={"content": [{"type": "text", "text": str(items)}]},
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
) -> Response:
    """
    Handle Razorpay webhook events.
    
    Verifies webhook signature using HMAC-SHA256.
    Implements idempotency using mandate_id from payload.
    """
    # Get raw body bytes
    body = await request.body()
    body_str = body.decode("utf-8")
    
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")
    
    try:
        # Verify signature using native HMAC-SHA256
        if not verify_razorpay_webhook_signature(
            body=body_str,
            signature=x_razorpay_signature,
            secret=settings.RAZORPAY_WEBHOOK_SECRET,
        ):
            raise ValueError("Signature mismatch")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse JSON payload
    import json
    payload = json.loads(body_str)
    
    # Extract mandate_id for idempotency (from entity or payment_link)
    mandate_id = None
    event_type = payload.get("event")
    
    # Razorpay webhook payload structure varies by event type
    # Common structure: {"event": "payment.captured", "payload": {"payment": {"entity": {...}}}}
    if "payload" in payload:
        entity = payload["payload"].get("payment", {}).get("entity", {})
        base_id = entity.get("order_id") or entity.get("id")
        # Include event_type to differentiate events for the same payment/order
        if base_id:
            mandate_id = f"{event_type}:{base_id}"
    
    # Fallback to event type if no mandate_id found
    if not mandate_id:
        mandate_id = f"{event_type}_{payload.get('created_at', '')}"
    
    # Check idempotency
    if mandate_id in _idempotency_keys:
        # Already processed - return success (idempotent)
        return Response(content='{"status": "already_processed"}', media_type="application/json")
    
    # Mark as processed
    _idempotency_keys.add(mandate_id)
    
    # TODO: Process webhook event (payment.captured, payment.failed, etc.)
    # This would typically update mandate status, trigger audit, etc.
    
    return Response(content='{"status": "success"}', media_type="application/json")


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