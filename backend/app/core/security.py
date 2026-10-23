from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"strict-origin-when-cross-origin"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                        (
                            b"content-security-policy",
                            b"default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
                            b"form-action 'self'; object-src 'none'",
                        ),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, requests_per_minute: int = 120):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") == "/api/v1/health":
            await self.app(scope, receive, send)
            return

        now = time.monotonic()
        client_info = scope.get("client")
        client = client_info[0] if client_info else "unknown"
        bucket = self.requests[client]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= self.requests_per_minute:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Limite de requisições excedido."},
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return
        bucket.append(now)
        await self.app(scope, receive, send)
