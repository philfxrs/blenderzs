"""针对离线规则 Planner 的单元测试。"""
from __future__ import annotations

from addons.ai_modeler.rules_planner import RulesPlanner


def test_generate_plan_with_material_and_boolean():
    planner = RulesPlanner()
    plan = planner.generate_plan("制作一个50cm的金属立方体并挖孔", units="CM")
    ops = [step.op for step in plan.steps]
    assert "ADD_CUBE" in ops
    assert "BOOLEAN_DIFFERENCE" in ops
    assert any(
        step.params.get("preset") == "metal_brushed"
        for step in plan.steps
        if step.op == "SET_MATERIAL"
    )


def test_generate_plan_with_array_and_bevel():
    planner = RulesPlanner()
    plan = planner.generate_plan(
        "create a radial array of cylinders with bevel",
        units="M",
    )
    ops = [step.op for step in plan.steps]
    assert "ADD_CYLINDER" in ops
    assert "ARRAY_RADIAL" in ops
    assert "BEVEL" in ops
