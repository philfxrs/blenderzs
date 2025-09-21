"""定义 AI Modeler 插件在 Blender UI 中的面板与列表。"""
from __future__ import annotations

import bpy
from bpy.types import Context, Panel, UIList


class AIModelerHistoryList(UIList):
    """自定义 UIList，用于在侧栏展示生成历史记录。"""

    bl_idname = "AI_MODEL_UL_history"

    def draw_item(
        self,
        context: Context,
        layout: bpy.types.UILayout,
        data: bpy.types.AnyType,
        item: bpy.types.PropertyGroup,
        icon: int,
        active_data: bpy.types.AnyType,
        active_propname: str,
        index: int,
    ) -> None:
        """绘制单条历史记录的 UI。"""
        # Blender 提供多种布局模式，默认/紧凑模式下展示更多文字。
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row()
            row.label(text=item.prompt[:24] if item.prompt else "<空>")
            row.label(text=item.status or "-")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text=item.status or "-")


class AIModelerPanel(Panel):
    """3D 视图侧栏中的主面板。"""

    bl_label = "AI Modeler"
    bl_idname = "VIEW3D_PT_ai_modeler"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI Modeler"

    def draw(self, context: Context) -> None:
        scene = context.scene
        layout = self.layout

        # 输入提示词与单位设置，单位用于后续规则 Planner 的尺寸推断。
        layout.prop(scene, "ai_modeler_prompt", text="提示词")
        layout.prop(scene, "ai_modeler_units", text="单位")

        row = layout.row()
        row.operator("ai_modeler.generate", text="生成模型", icon="PLAY")

        layout.separator()
        layout.label(text="历史记录")
        layout.template_list(
            "AI_MODEL_UL_history",
            "history",
            scene,
            "ai_modeler_history",
            scene,
            "ai_modeler_history_index",
        )
        layout.operator(
            "ai_modeler.history_clear",
            text="清空历史",
            icon="TRASH",
        )

        layout.separator()
        layout.label(text="导出")
        row = layout.row(align=True)
        row.operator("ai_modeler.export_glb", text="导出 GLB", icon="EXPORT")
        row.operator("ai_modeler.export_fbx", text="导出 FBX", icon="EXPORT")
        row.operator("ai_modeler.export_obj", text="导出 OBJ", icon="EXPORT")

        if scene.ai_modeler_last_error:
            # 将最近一次错误以显著方式展示给用户。
            box = layout.box()
            box.label(text="最近错误", icon="ERROR")
            box.label(text=scene.ai_modeler_last_error)
