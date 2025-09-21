"""基于规则的离线 Planner。"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from .schemas import ModelingPlan, PlanStep

_UNIT_ALIAS = {
    "米": "M",
    "m": "M",
    "厘米": "CM",
    "cm": "CM",
    "毫米": "MM",
    "mm": "MM",
}


@dataclass
class ParsedDimension:
    value: float
    unit: str


class RulesPlanner:
    """通过简单的模式匹配将自然语言提示转换为建模计划。"""

    def generate_plan(self, prompt: str, units: str = "M") -> ModelingPlan:
        plan = ModelingPlan(id=str(uuid.uuid4()), prompt=prompt, units=units)
        normalized = prompt.lower()
        steps: list[PlanStep] = []
        default_unit = units or "M"

        dims = self._extract_dimensions(prompt)
        size_value = dims[0].value if dims else 1.0
        size_unit = dims[0].unit if dims else default_unit

        last_object_name = None

        if any(keyword in normalized for keyword in ["cube", "立方", "正方体"]):
            last_object_name = "AI_Cube"
            steps.append(
                PlanStep(
                    op="ADD_CUBE",
                    params={
                        "size": size_value,
                        "units": size_unit,
                        "name": last_object_name,
                    },
                    notes="创建基础立方体",
                )
            )

        if any(keyword in normalized for keyword in ["sphere", "球"]):
            last_object_name = "AI_Sphere"
            steps.append(
                PlanStep(
                    op="ADD_SPHERE",
                    params={
                        "radius": size_value / 2,
                        "units": size_unit,
                        "name": last_object_name,
                    },
                    notes="创建球体",
                )
            )

        if any(keyword in normalized for keyword in ["cylinder", "圆柱"]):
            last_object_name = "AI_Cylinder"
            steps.append(
                PlanStep(
                    op="ADD_CYLINDER",
                    params={
                        "radius": size_value / 2,
                        "depth": size_value,
                        "units": size_unit,
                        "name": last_object_name,
                    },
                    notes="创建圆柱体",
                )
            )

        if "阵列" in prompt or "radial" in normalized or "array" in normalized:
            target = last_object_name or "AI_Cube"
            steps.append(
                PlanStep(
                    op="ARRAY_RADIAL",
                    params={
                        "source": target,
                        "count": 8,
                        "radius": size_value,
                        "units": size_unit,
                    },
                    notes="创建环形阵列",
                )
            )

        if "倒角" in prompt or "bevel" in normalized:
            target = last_object_name or "AI_Cube"
            steps.append(
                PlanStep(
                    op="BEVEL",
                    params={
                        "target": target,
                        "width": size_value * 0.05,
                        "units": size_unit,
                        "segments": 3,
                    },
                    notes="为对象添加倒角",
                )
            )

        if any(keyword in prompt for keyword in ["挖", "孔", "boolean", "布尔"]):
            base = "AI_Cube"
            cutter = "AI_Cylinder"
            if not any(step.op == "ADD_CUBE" for step in steps):
                steps.insert(
                    0,
                    PlanStep(
                        op="ADD_CUBE",
                        params={"size": size_value, "units": size_unit, "name": base},
                        notes="布尔操作基础体",
                    ),
                )
            if not any(step.op == "ADD_CYLINDER" for step in steps):
                steps.append(
                    PlanStep(
                        op="ADD_CYLINDER",
                        params={
                            "radius": size_value / 4,
                            "depth": size_value,
                            "units": size_unit,
                            "name": cutter,
                        },
                        notes="布尔操作切割体",
                    ),
                )
            steps.append(
                PlanStep(
                    op="BOOLEAN_DIFFERENCE",
                    params={"target": base, "cutter": cutter},
                    notes="执行布尔差集",
                )
            )

        material = self._match_material(prompt)
        if material:
            target = last_object_name or "AI_Cube"
            steps.append(
                PlanStep(
                    op="SET_MATERIAL",
                    params={"target": target, "preset": material},
                    notes="应用材质预设",
                )
            )

        plan.steps = steps
        return plan

    # ------------------------------------------------------------------
    # 文本解析辅助函数
    # ------------------------------------------------------------------
    def _extract_dimensions(self, prompt: str) -> list[ParsedDimension]:
        pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(mm|cm|m|米|厘米|毫米)")
        dims: list[ParsedDimension] = []
        for match in pattern.finditer(prompt.lower()):
            value = float(match.group(1))
            unit_raw = match.group(2)
            unit = _UNIT_ALIAS.get(unit_raw, unit_raw.upper())
            dims.append(ParsedDimension(value=value, unit=unit))
        return dims

    def _match_material(self, prompt: str) -> str | None:
        if any(keyword in prompt for keyword in ["金属", "metal"]):
            return "metal_brushed"
        if any(keyword in prompt for keyword in ["塑料", "plastic"]):
            return "plastic"
        if any(keyword in prompt for keyword in ["木", "wood"]):
            return "wood"
        return None


__all__ = ["RulesPlanner"]
