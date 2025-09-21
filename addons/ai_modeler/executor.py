"""执行 ModelingPlan 中定义的建模步骤。"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - pytest 默认没有 bpy 环境
    import bpy
except Exception:  # pragma: no cover - 兼容离线测试
    bpy = None  # type: ignore

from .exceptions import AIModelerError
from .materials import apply_material_preset
from .schemas import ExecutionResult, ModelingPlan

logger = logging.getLogger(__name__)


@dataclass
class _StepContext:
    """封装执行步骤时的上下文信息，便于回滚。"""

    created_objects: list[str]
    added_modifiers: list[tuple[str, str]]


class ModelingExecutor:
    """根据计划调用 Blender API 的执行器。

    该执行器具备“事务”能力：当任意步骤抛出异常时，会删除所有新建对象、移除新增的修改器，确保场景恢复到执行前状态。
    """

    def __init__(self, context: Any) -> None:
        if bpy is None:
            raise AIModelerError("当前环境缺少 bpy，无法执行建模操作")
        self.context = context
        self.scene = context.scene

    def execute_plan(self, plan: ModelingPlan) -> ExecutionResult:
        logger.info("开始执行建模方案：%s", plan.id)
        step_ctx = _StepContext(created_objects=[], added_modifiers=[])
        diff: list[dict[str, Any]] = []
        status = "success"
        error_msg = None

        for index, step in enumerate(plan.steps, start=1):
            try:
                logger.info("执行步骤 %d：%s", index, step.op)
                handler = self._get_handler(step.op)
                handler(step.params, step_ctx)
                diff.append({"step": step.op, "params": step.params})
            except Exception as exc:  # pragma: no cover - 运行时异常难覆盖
                logger.exception("步骤 %d 执行失败：%s", index, exc)
                error_msg = f"步骤 {index} ({step.op}) 失败：{exc}"
                status = "partial" if index > 1 else "fail"
                self._rollback(step_ctx)
                break

        logger.info("建模方案执行结束：%s", status)
        return ExecutionResult(
            status=status,
            objects=step_ctx.created_objects.copy(),
            diff=diff,
            error=error_msg,
        )

    # ------------------------------------------------------------------
    # 事务相关工具方法
    # ------------------------------------------------------------------
    def _rollback(self, step_ctx: _StepContext) -> None:
        """回滚执行过程中产生的改动。"""
        logger.info("执行回滚，删除新建对象并清理修改器")
        for obj_name in reversed(step_ctx.created_objects):
            obj = self.scene.objects.get(obj_name)
            if obj is None:
                continue
            logger.debug("删除对象：%s", obj_name)
            self.scene.collection.objects.unlink(obj)
            bpy.data.objects.remove(obj)
        for obj_name, modifier_name in step_ctx.added_modifiers:
            obj = self.scene.objects.get(obj_name)
            if obj is None:
                continue
            modifier = obj.modifiers.get(modifier_name)
            if modifier:
                logger.debug("移除修改器 %s.%s", obj_name, modifier_name)
                obj.modifiers.remove(modifier)

    # ------------------------------------------------------------------
    # 步骤处理函数
    # ------------------------------------------------------------------
    def _get_handler(self, op: str) -> Callable[[dict[str, Any], _StepContext], None]:
        handlers = {
            "ADD_CUBE": self._op_add_cube,
            "ADD_SPHERE": self._op_add_sphere,
            "ADD_CYLINDER": self._op_add_cylinder,
            "BOOLEAN_DIFFERENCE": self._op_boolean_difference,
            "ARRAY_RADIAL": self._op_array_radial,
            "BEVEL": self._op_bevel,
            "SET_MATERIAL": self._op_set_material,
        }
        if op not in handlers:
            raise AIModelerError(f"暂不支持的操作：{op}")
        return handlers[op]

    def _convert_length(self, value: float, unit: str | None) -> float:
        """将各种单位转换为 Blender 使用的米。"""
        if unit is None or unit.upper() == "M":
            return value
        if unit.upper() == "CM":
            return value / 100
        if unit.upper() == "MM":
            return value / 1000
        logger.warning("未知单位 %s，按米处理", unit)
        return value

    def _op_add_cube(self, params: dict[str, Any], step_ctx: _StepContext) -> None:
        size = self._convert_length(float(params.get("size", 1.0)), params.get("units"))
        name = params.get("name", "AI_Cube")
        bpy.ops.mesh.primitive_cube_add(size=size)
        obj = bpy.context.active_object
        if obj is None:
            raise AIModelerError("创建立方体失败")
        obj.name = name
        step_ctx.created_objects.append(obj.name)

    def _op_add_sphere(self, params: dict[str, Any], step_ctx: _StepContext) -> None:
        radius = self._convert_length(
            float(params.get("radius", 0.5)), params.get("units")
        )
        name = params.get("name", "AI_Sphere")
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius)
        obj = bpy.context.active_object
        if obj is None:
            raise AIModelerError("创建球体失败")
        obj.name = name
        step_ctx.created_objects.append(obj.name)

    def _op_add_cylinder(self, params: dict[str, Any], step_ctx: _StepContext) -> None:
        radius = self._convert_length(
            float(params.get("radius", 0.5)), params.get("units")
        )
        depth = self._convert_length(
            float(params.get("depth", 1.0)), params.get("units")
        )
        name = params.get("name", "AI_Cylinder")
        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth)
        obj = bpy.context.active_object
        if obj is None:
            raise AIModelerError("创建圆柱体失败")
        obj.name = name
        step_ctx.created_objects.append(obj.name)

    def _op_boolean_difference(
        self, params: dict[str, Any], step_ctx: _StepContext
    ) -> None:
        target_name = params.get("target")
        cutter_name = params.get("cutter")
        if not target_name or not cutter_name:
            raise AIModelerError("BOOLEAN_DIFFERENCE 需要 target 与 cutter 参数")
        target = self.scene.objects.get(target_name)
        cutter = self.scene.objects.get(cutter_name)
        if target is None or cutter is None:
            raise AIModelerError("布尔运算对象不存在")
        modifier = target.modifiers.new(name="AI_Boolean", type="BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.object = cutter
        step_ctx.added_modifiers.append((target.name, modifier.name))

    def _op_array_radial(self, params: dict[str, Any], step_ctx: _StepContext) -> None:
        source_name = params.get("source")
        if not source_name:
            raise AIModelerError("ARRAY_RADIAL 需要 source 参数")
        source = self.scene.objects.get(source_name)
        if source is None:
            raise AIModelerError("源对象不存在")
        count = int(params.get("count", 6))
        radius = self._convert_length(
            float(params.get("radius", 1.0)), params.get("units")
        )

        empty = bpy.data.objects.new(f"{source_name}_RadialEmpty", None)
        self.scene.collection.objects.link(empty)
        step_ctx.created_objects.append(empty.name)

        modifier = source.modifiers.new(name="AI_Array", type="ARRAY")
        modifier.count = max(1, count)
        modifier.use_relative_offset = False
        modifier.use_object_offset = True
        modifier.offset_object = empty
        empty.rotation_euler[2] = 6.283185307179586 / max(1, count)
        empty.location.x = radius
        step_ctx.added_modifiers.append((source.name, modifier.name))

    def _op_bevel(self, params: dict[str, Any], step_ctx: _StepContext) -> None:
        target_name = params.get("target")
        if not target_name:
            raise AIModelerError("BEVEL 需要 target 参数")
        target = self.scene.objects.get(target_name)
        if target is None:
            raise AIModelerError("倒角对象不存在")
        width = self._convert_length(
            float(params.get("width", 0.01)), params.get("units")
        )
        segments = int(params.get("segments", 2))
        modifier = target.modifiers.new(name="AI_Bevel", type="BEVEL")
        modifier.width = width
        modifier.segments = max(1, segments)
        modifier.limit_method = "NONE"
        step_ctx.added_modifiers.append((target.name, modifier.name))

    def _op_set_material(self, params: dict[str, Any], step_ctx: _StepContext) -> None:
        target_name = params.get("target")
        preset = params.get("preset")
        if not target_name or not preset:
            raise AIModelerError("SET_MATERIAL 需要 target 与 preset 参数")
        target = self.scene.objects.get(target_name)
        if target is None:
            raise AIModelerError("设置材质的对象不存在")
        apply_material_preset(target, preset)


__all__ = ["ModelingExecutor"]
