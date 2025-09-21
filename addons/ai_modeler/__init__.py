"""AI Modeler Blender 插件入口模块。

该模块负责定义插件的元数据、注册 UI 面板、操作符、属性等。
"""

from __future__ import annotations

import logging

try:  # pragma: no cover - 测试环境可能不存在 bpy
    import bpy
    from bpy.props import (
        CollectionProperty,
        EnumProperty,
        IntProperty,
        StringProperty,
    )
    from bpy.types import AddonPreferences, PropertyGroup
except ModuleNotFoundError:  # pragma: no cover
    bpy = None  # type: ignore
    CollectionProperty = EnumProperty = IntProperty = StringProperty = None  # type: ignore
    AddonPreferences = PropertyGroup = object  # type: ignore

if bpy is not None:
    from . import materials
    from .operators import (
        AIModelerExportFBXOperator,
        AIModelerExportGLBOperator,
        AIModelerExportOBJOperator,
        AIModelerGenerateOperator,
        AIModelerHistoryClearOperator,
    )
    from .ui_panel import (
        AIModelerHistoryList,
        AIModelerPanel,
    )

logger = logging.getLogger(__name__)

bl_info = {
    "name": "AI Modeler",
    "author": "AI Modeler Team",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > AI Modeler",
    "description": "使用自然语言快速生成 3D 模型的工具",
    "warning": "MVP 原型，可能存在功能限制",
    "doc_url": "https://github.com/example/ai-modeler",
    "category": "3D View",
}


if bpy is not None:

    class AIModelerPreferences(AddonPreferences):
        """插件偏好设置，允许配置在线 Planner 服务。"""

        bl_idname = __package__

        base_url: StringProperty(
            name="Planner 服务地址",
            description="可选，配置在线 LLM Planner 的 HTTP 接口地址",
            default="",
        )
        api_key: StringProperty(
            name="API Key",
            description="访问在线 Planner 所需的密钥",
            subtype="PASSWORD",
            default="",
        )
        timeout: IntProperty(
            name="请求超时 (秒)",
            description="调用在线 Planner 时的超时时间",
            default=15,
            min=1,
            max=120,
        )

        def draw(self, context: bpy.types.Context) -> None:  # type: ignore[override]
            layout = self.layout
            layout.label(text="在线 Planner 设置（可选）")
            layout.prop(self, "base_url")
            layout.prop(self, "api_key")
            layout.prop(self, "timeout")
            layout.label(text="不配置时自动回退到内置规则 Planner")


    class AIModelerHistoryItem(PropertyGroup):
        """用于展示历史记录的属性组。"""

        prompt: StringProperty(name="提示词", default="")
        plan_id: StringProperty(name="方案 ID", default="")
        status: StringProperty(name="执行状态", default="")
        summary: StringProperty(name="摘要", default="")
        error: StringProperty(name="错误信息", default="")


    CLASSES: list[type] = [
        AIModelerPreferences,
        AIModelerHistoryItem,
        AIModelerPanel,
        AIModelerHistoryList,
        AIModelerGenerateOperator,
        AIModelerExportGLBOperator,
        AIModelerExportFBXOperator,
        AIModelerExportOBJOperator,
        AIModelerHistoryClearOperator,
    ]
else:  # pragma: no cover - 用于非 Blender 测试环境
    CLASSES: list[type] = []


def register() -> None:
    if bpy is None:  # pragma: no cover - 单元测试环境
        raise RuntimeError("bpy 不可用，无法注册 AI Modeler 插件")
    logging.basicConfig(level=logging.INFO)
    materials.ensure_material_presets_loaded()
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ai_modeler_prompt = StringProperty(
        name="自然语言描述",
        description="输入希望生成的模型描述，可使用中文或英文",
        default="",
    )
    bpy.types.Scene.ai_modeler_units = EnumProperty(
        name="单位",
        description="输入尺寸时使用的单位，将自动换算为米",
        items=[
            ("M", "米", "单位为米"),
            ("CM", "厘米", "单位为厘米"),
            ("MM", "毫米", "单位为毫米"),
        ],
        default="M",
    )
    bpy.types.Scene.ai_modeler_history = CollectionProperty(type=AIModelerHistoryItem)
    bpy.types.Scene.ai_modeler_history_index = IntProperty(default=-1)
    bpy.types.Scene.ai_modeler_last_error = StringProperty(default="")


def unregister() -> None:
    if bpy is None:  # pragma: no cover
        return
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ai_modeler_prompt
    del bpy.types.Scene.ai_modeler_units
    del bpy.types.Scene.ai_modeler_history
    del bpy.types.Scene.ai_modeler_history_index
    del bpy.types.Scene.ai_modeler_last_error


__all__ = [
    "register",
    "unregister",
]
