"""Centralized OpenAPI metadata configuration."""

from typing import Any

# API Tags Metadata for grouping endpoints
tags_metadata: list[dict[str, Any]] = [
    {
        "name": "Health",
        "description": "System health and database connectivity checks.",
    },
]

# Contact Information
contact_info: dict[str, str] = {
    "name": "AI Marketplace API Team",
    "url": "https://ai-marketplace.example/support",
}

# License Information
license_info: dict[str, str] = {
    "name": "Proprietary",
    "url": "https://ai-marketplace.example/terms",
}
