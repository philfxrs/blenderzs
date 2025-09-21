"""简易 HTTP 客户端，负责与在线 Planner 服务交互。"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from .exceptions import AIHttpError

logger = logging.getLogger(__name__)


class HttpClient:
    """使用标准库实现的轻量 HTTP 封装，支持重试。"""

    def __init__(
        self, base_url: str, timeout: int = 15, api_key: str | None = None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or ""
        self.max_retries = 3

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-Modeler-Addon/0.1",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    status = response.getcode()
                    body = response.read().decode("utf-8")
                    if status >= 400:
                        raise AIHttpError(f"HTTP {status}: {body}", status_code=status)
                    return json.loads(body or "{}")
            except (urllib.error.URLError, TimeoutError, AIHttpError) as exc:
                last_error = exc
                logger.warning("HTTP 请求失败（第 %d 次尝试）：%s", attempt, exc)
                time.sleep(0.5 * attempt)
        raise AIHttpError(f"请求失败：{last_error}")


__all__ = ["HttpClient"]
