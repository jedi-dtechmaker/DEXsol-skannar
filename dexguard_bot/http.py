from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class HttpError(RuntimeError):
    pass


class ReadTimeout(HttpError):
    pass


def _safe_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = parts.path
    if "/bot" in path:
        prefix, _, rest = path.partition("/bot")
        if "/" in rest:
            _, suffix = rest.split("/", 1)
            path = f"{prefix}/bot[redacted]/{suffix}"
        else:
            path = f"{prefix}/bot[redacted]"
    if "/v2/" in path:
        prefix, _, rest = path.partition("/v2/")
        suffix = ""
        if "/" in rest:
            _, suffix = rest.split("/", 1)
            suffix = f"/{suffix}"
        path = f"{prefix}/v2/[redacted]{suffix}"
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def get_json(url: str, timeout: int = 15, params: dict[str, Any] | None = None) -> Any:
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "DexGuardBot/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise HttpError(f"GET {_safe_url(url)} failed with HTTP {exc.code}: {body[:300]}") from exc
    except TimeoutError as exc:
        raise ReadTimeout(f"GET {_safe_url(url)} timed out") from exc
    except socket.timeout as exc:
        raise ReadTimeout(f"GET {_safe_url(url)} timed out") from exc
    except urllib.error.URLError as exc:
        if _is_timeout_reason(exc.reason):
            raise ReadTimeout(f"GET {_safe_url(url)} timed out") from exc
        raise HttpError(f"GET {_safe_url(url)} failed: {exc.reason}") from exc


def post_json(url: str, payload: dict[str, Any], timeout: int = 15) -> Any:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "DexGuardBot/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise HttpError(f"POST {_safe_url(url)} failed with HTTP {exc.code}: {body[:300]}") from exc
    except TimeoutError as exc:
        raise ReadTimeout(f"POST {_safe_url(url)} timed out") from exc
    except socket.timeout as exc:
        raise ReadTimeout(f"POST {_safe_url(url)} timed out") from exc
    except urllib.error.URLError as exc:
        if _is_timeout_reason(exc.reason):
            raise ReadTimeout(f"POST {_safe_url(url)} timed out") from exc
        raise HttpError(f"POST {_safe_url(url)} failed: {exc.reason}") from exc


def _is_timeout_reason(reason: Any) -> bool:
    if isinstance(reason, TimeoutError):
        return True
    if isinstance(reason, socket.timeout):
        return True
    return "timed out" in str(reason).lower()
