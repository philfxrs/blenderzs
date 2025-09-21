"""针对执行器的最小化测试，用于验证步骤执行流程。"""
from __future__ import annotations

import pytest

try:  # pragma: no cover - pytest 可能不存在 bpy
    import bpy
except Exception:  # pragma: no cover
    bpy = None  # type: ignore

from addons.ai_modeler.executor import ModelingExecutor
from addons.ai_modeler.schemas import ModelingPlan, PlanStep


@pytest.mark.skipif(bpy is None, reason="当前环境缺少 bpy")
def test_execute_add_cube():
    plan = ModelingPlan(
        id="test",
        prompt="add cube",
        units="M",
        steps=[
            PlanStep(
                op="ADD_CUBE",
                params={"size": 1, "units": "M", "name": "TestCube"},
            )
        ],
    )
    executor = ModelingExecutor(bpy.context)
    result = executor.execute_plan(plan)
    assert "TestCube" in result.objects
    obj = bpy.data.objects.get("TestCube")
    assert obj is not None
    bpy.data.objects.remove(obj)
