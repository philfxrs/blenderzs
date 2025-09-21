"""定义所有可交互的 Blender Operator。"""
from __future__ import annotations

import logging

import bpy
from bpy.props import StringProperty
from bpy.types import Context, Operator

from .exceptions import AIModelerError
from .executor import ModelingExecutor
from .planner_client import PlannerClient
from .rules_planner import RulesPlanner

logger = logging.getLogger(__name__)

# 内置规则 Planner 单例，避免重复解析 JSON 预设。
RULES_PLANNER = RulesPlanner()


class AIModelerGenerateOperator(Operator):
    """根据提示词生成模型的操作符。"""

    bl_idname = "ai_modeler.generate"
    bl_label = "生成模型"
    bl_description = "调用 Planner 解析提示词并执行建模步骤"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: Context):  # type: ignore[override]
        scene = context.scene
        prompt = scene.ai_modeler_prompt.strip()
        if not prompt:
            self.report({"WARNING"}, "请输入提示词后再生成模型")
            return {"CANCELLED"}

        units = scene.ai_modeler_units or "M"
        plan = None
        used_remote = False

        # 读取插件偏好设置，决定是否尝试调用在线 Planner。
        addon_prefs = context.preferences.addons.get(__package__)
        if addon_prefs and addon_prefs.preferences.base_url:
            prefs = addon_prefs.preferences
            client = PlannerClient(
                base_url=prefs.base_url,
                api_key=prefs.api_key,
                timeout=prefs.timeout,
            )
            try:
                plan = client.generate_plan(prompt=prompt, units=units)
                used_remote = True
                logger.info("使用在线 Planner 生成方案：%s", plan.id)
            except Exception as exc:  # pragma: no cover - 依赖网络
                logger.warning("在线 Planner 失败，回退到规则解析：%s", exc)
                self.report({"WARNING"}, f"在线 Planner 失败，自动回退：{exc}")

        if plan is None:
            plan = RULES_PLANNER.generate_plan(prompt=prompt, units=units)
            logger.info("使用规则 Planner 生成方案：%s", plan.id)

        executor = ModelingExecutor(context)
        try:
            result = executor.execute_plan(plan)
        except AIModelerError as exc:
            # 发生错误时记录日志，并向 UI 展示。
            logger.exception("执行模型方案失败：%s", exc)
            scene.ai_modeler_last_error = str(exc)
            self._append_history(scene, plan.id, prompt, "fail", str(exc), [])
            self.report({"ERROR"}, f"执行失败：{exc}")
            return {"CANCELLED"}

        scene.ai_modeler_last_error = result.error or ""
        self._append_history(
            scene,
            plan.id,
            prompt,
            result.status,
            result.error or ("使用在线 Planner" if used_remote else "使用离线 Planner"),
            result.objects,
        )

        if result.status == "success":
            self.report({"INFO"}, "模型生成成功")
        elif result.status == "partial":
            self.report({"WARNING"}, "部分步骤执行失败，请查看日志")
        else:
            self.report({"ERROR"}, result.error or "未知错误")
        return {"FINISHED"}

    def _append_history(
        self,
        scene: bpy.types.Scene,
        plan_id: str,
        prompt: str,
        status: str,
        message: str,
        objects: list[str],
    ) -> None:
        """将执行结果写入历史记录列表。"""
        item = scene.ai_modeler_history.add()
        item.plan_id = plan_id
        item.prompt = prompt
        item.status = status
        item.summary = ", ".join(objects) if objects else message
        item.error = message if status != "success" else ""
        scene.ai_modeler_history_index = len(scene.ai_modeler_history) - 1


class _BaseExportOperator(Operator):
    """导出通用逻辑基类。"""

    filter_glob: StringProperty(options={"HIDDEN"})
    filepath: StringProperty(subtype="FILE_PATH")

    def invoke(self, context: Context, event):  # type: ignore[override]
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class AIModelerExportGLBOperator(_BaseExportOperator):
    """导出场景为 GLB。"""

    bl_idname = "ai_modeler.export_glb"
    bl_label = "导出 GLB"
    filename_ext = ".glb"
    filter_glob: StringProperty(default="*.glb", options={"HIDDEN"})

    def execute(self, context: Context):  # type: ignore[override]
        if not self.filepath:
            self.report({"ERROR"}, "请选择导出路径")
            return {"CANCELLED"}
        bpy.ops.export_scene.gltf(
            filepath=self.filepath,
            export_format="GLB",
            export_apply=True,
        )
        self.report({"INFO"}, "已导出 GLB")
        return {"FINISHED"}


class AIModelerExportFBXOperator(_BaseExportOperator):
    """导出场景为 FBX。"""

    bl_idname = "ai_modeler.export_fbx"
    bl_label = "导出 FBX"
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={"HIDDEN"})

    def execute(self, context: Context):  # type: ignore[override]
        if not self.filepath:
            self.report({"ERROR"}, "请选择导出路径")
            return {"CANCELLED"}
        bpy.ops.export_scene.fbx(
            filepath=self.filepath,
            apply_unit_scale=True,
            bake_space_transform=True,
        )
        self.report({"INFO"}, "已导出 FBX")
        return {"FINISHED"}


class AIModelerExportOBJOperator(_BaseExportOperator):
    """导出场景为 OBJ。"""

    bl_idname = "ai_modeler.export_obj"
    bl_label = "导出 OBJ"
    filename_ext = ".obj"
    filter_glob: StringProperty(default="*.obj", options={"HIDDEN"})

    def execute(self, context: Context):  # type: ignore[override]
        if not self.filepath:
            self.report({"ERROR"}, "请选择导出路径")
            return {"CANCELLED"}
        bpy.ops.export_scene.obj(
            filepath=self.filepath,
            use_selection=False,
            axis_forward="-Z",
            axis_up="Y",
        )
        self.report({"INFO"}, "已导出 OBJ")
        return {"FINISHED"}


class AIModelerHistoryClearOperator(Operator):
    """清空历史记录。"""

    bl_idname = "ai_modeler.history_clear"
    bl_label = "清空历史"

    def execute(self, context: Context):  # type: ignore[override]
        context.scene.ai_modeler_history.clear()
        context.scene.ai_modeler_last_error = ""
        self.report({"INFO"}, "历史记录已清空")
        return {"FINISHED"}


__all__ = [
    "AIModelerGenerateOperator",
    "AIModelerExportGLBOperator",
    "AIModelerExportFBXOperator",
    "AIModelerExportOBJOperator",
    "AIModelerHistoryClearOperator",
]
