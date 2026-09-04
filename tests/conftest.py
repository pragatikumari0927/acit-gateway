"""Shared pytest env so src.config.settings can load during collection."""

from __future__ import annotations

import os

os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_key")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "rzp_test_secret")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")
os.environ.setdefault("JWT_SECRET", "this_is_a_32_character_secret_xx")
os.environ.setdefault("API_KEY", "test_api_key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("MCP_ENABLED", "false")
os.environ.setdefault("CHAOS_ENABLED", "false")
