from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post_json(
    *,
    url: str,
    payload: dict[str, Any],
    timeout_sec: int,
    api_key: str | None = None,
) -> Any:
    """POST JSON to a TEI-compatible endpoint and parse the JSON response."""

    headers = {"Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = Request(
        url=url,
        method="POST",
        headers=headers,
        data=json.dumps(payload).encode("utf-8"),
    )

    try:
        with urlopen(request, timeout=timeout_sec) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"TEI HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"TEI transport error: {exc}") from exc

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("TEI вернул невалидный JSON") from exc
