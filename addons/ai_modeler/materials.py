"""材质相关的工具函数。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

try:  # pragma: no cover - pytest 环境无 bpy
    import bpy
except Exception:  # pragma: no cover - 兼容离线测试
    bpy = None  # type: ignore

from .exceptions import AIModelerError

logger = logging.getLogger(__name__)

_PRESETS: dict[str, dict[str, Any]] = {}
_PRESET_PATH = Path(__file__).resolve().parent / "presets" / "materials.json"


def ensure_material_presets_loaded() -> None:
    """在注册插件时读取材质预设。"""
    global _PRESETS
    if _PRESETS:
        return
    try:
        with _PRESET_PATH.open("r", encoding="utf-8") as fh:
            _PRESETS = json.load(fh)
        logger.info("已加载材质预设：%s", list(_PRESETS.keys()))
    except FileNotFoundError as exc:  # pragma: no cover - 安装包缺失才会发生
        logger.error("未找到材质预设文件：%s", exc)
        _PRESETS = {}


def get_preset(name: str) -> dict[str, Any]:
    ensure_material_presets_loaded()
    preset = _PRESETS.get(name)
    if not preset:
        raise AIModelerError(f"未知材质预设：{name}")
    return preset


def apply_material_preset(obj: Any, preset_name: str) -> None:
    """将指定材质预设应用到对象上。"""
    if bpy is None:
        raise AIModelerError("当前环境不支持材质操作（缺少 bpy）")
    preset = get_preset(preset_name)
    mat_name = f"AI_{preset_name}"
    material = bpy.data.materials.get(mat_name)
    if material is None:
        material = bpy.data.materials.new(mat_name)
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            # 按预设配置基础参数，主要覆盖金属度、粗糙度、基础颜色等。
            bsdf.inputs["Base Color"].default_value = preset.get(
                "base_color", [1, 1, 1, 1]
            )
            bsdf.inputs["Metallic"].default_value = preset.get("metallic", 0.0)
            bsdf.inputs["Roughness"].default_value = preset.get("roughness", 0.5)
    if obj.data is None:
        raise AIModelerError("对象无可用几何数据，无法设置材质")
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


__all__ = ["ensure_material_presets_loaded", "apply_material_preset", "get_preset"]
