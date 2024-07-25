"""Utilities for the nice_go package."""

from __future__ import annotations

import json
from typing import Any

from nice_go._const import REQUEST_TEMPLATES


async def get_request_template(
    request_name: str,
    arguments: dict[str, str] | None,
) -> Any:
    """Get a request template with optional arguments.

    Args:
        request_name: The name of the request template.
        arguments: Optional arguments to replace in the template.

    Returns:
        The request template with optional arguments.
    """
    template = json.dumps(REQUEST_TEMPLATES[request_name])
    if arguments:
        for key, value in arguments.items():
            template = template.replace(f"${key}", value)
    return json.loads(template)
