"""定义插件内部使用的数据结构。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class PlanStep:
    """单条建模步骤。"""

    op: str
    params: dict[str, Any]
    notes: str | None = None


@dataclass
class ModelingPlan:
    """建模计划，包含原始提示词与步骤列表。"""

    id: str
    prompt: str
    units: str
    steps: list[PlanStep] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """执行器运行后的结果。"""

    status: Literal["success", "partial", "fail"]
    objects: list[str]
    diff: list[dict[str, Any]]
    error: str | None = None


__all__ = ["PlanStep", "ModelingPlan", "ExecutionResult"]
