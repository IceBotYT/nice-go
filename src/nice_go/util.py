from __future__ import annotations

import json
from typing import Any

from nice_go.const import REQUEST_TEMPLATES


async def get_request_template(
    request_name: str,
    arguments: dict[str, str] | None,
) -> Any:
    template = json.dumps(REQUEST_TEMPLATES[request_name])
    if arguments:
        for key, value in arguments.items():
            template = template.replace(f"${key}", value)
    return json.loads(template)
