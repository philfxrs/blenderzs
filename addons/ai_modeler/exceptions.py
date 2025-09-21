"""定义插件内部使用的自定义异常类型。"""
from __future__ import annotations


class AIModelerError(Exception):
    """基础异常类型，所有业务异常均应继承该类。"""


class AIHttpError(AIModelerError):
    """网络相关错误，例如 HTTP 请求失败或超时。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
