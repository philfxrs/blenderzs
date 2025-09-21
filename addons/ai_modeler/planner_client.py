"""在线 Planner 客户端封装。"""
from __future__ import annotations

import logging
from typing import Any

from .exceptions import AIModelerError
from .http_client import HttpClient
from .schemas import ModelingPlan, PlanStep

logger = logging.getLogger(__name__)


class PlannerClient:
    """负责调用远端 LLM Planner 服务并转换为内部数据结构。"""

    def __init__(self, base_url: str, api_key: str, timeout: int = 15) -> None:
        if not base_url:
            raise AIModelerError("必须提供 Planner 服务地址")
        self.http = HttpClient(base_url=base_url, timeout=timeout, api_key=api_key)

    def generate_plan(self, prompt: str, units: str = "M") -> ModelingPlan:
        logger.info("调用在线 Planner 生成模型方案")
        payload = {"prompt": prompt, "units": units}
        response = self.http.post("/plan", payload)
        plan_data = response.get("plan", response)
        required_keys = {"id", "prompt", "units", "steps"}
        if not required_keys.issubset(plan_data):
            raise AIModelerError("Planner 返回数据不完整")
        steps = [self._parse_step(step) for step in plan_data.get("steps", [])]
        return ModelingPlan(
            id=str(plan_data.get("id")),
            prompt=str(plan_data.get("prompt")),
            units=str(plan_data.get("units", units)),
            steps=steps,
        )

    def _parse_step(self, step_data: dict[str, Any]) -> PlanStep:
        op = step_data.get("op")
        params = step_data.get("params", {})
        notes = step_data.get("notes")
        if not op:
            raise AIModelerError("Planner 返回的步骤缺少 op 字段")
        if not isinstance(params, dict):
            raise AIModelerError("步骤参数必须是字典")
        return PlanStep(op=str(op), params=params, notes=notes)


__all__ = ["PlannerClient"]
