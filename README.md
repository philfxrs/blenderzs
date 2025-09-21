# AI Modeler Blender Add-on

“AI Modeler” 是一个基于 Blender 4.x 的自然语言建模插件，提供离线规则 Planner 与可配置的在线 LLM Planner，帮助创作者用中文或英文快速搭建基础几何场景。

## 功能概览

- 侧栏面板输入自然语言提示词，一键生成模型。
- 离线规则 Planner 支持常见几何体、布尔运算、阵列、倒角、材质设定。
- 执行器具备事务回滚能力，失败时自动清理新增对象。
- 预置金属、塑料、木质材质，可在建模后快速套用。
- 支持导出 GLB/FBX/OBJ，便于与其他 DCC/游戏引擎协同。
- 可配置在线 Planner 服务（HTTP POST `/plan` 接口），实现更复杂的方案规划。

## 安装与打包

1. 克隆或下载本仓库。
2. 执行 `make zip`，自动在当前目录生成 `ai_modeler.zip`。
3. 打开 Blender 4.x，依次进入 `Edit > Preferences > Add-ons > Install...`，选择生成的 `ai_modeler.zip`。
4. 启用 “AI Modeler” 插件后，在 3D 视图侧栏（快捷键 `N`）即可看到 “AI Modeler” 面板。

> 提示：Zip 包内仅包含 `addons/ai_modeler`，方便直接安装或在部署时上传。

## 本地开发与测试

### Python 依赖

插件运行完全依赖 Blender 自带 Python，无需额外安装依赖。仓库仅提供 `pyproject.toml` 以便在编辑器中运行 Ruff/Black 等静态检查工具。

### 运行单元测试

```bash
# 纯 Python 规则 Planner 测试
pytest addons/ai_modeler/tests/test_rules_planner.py
```

如果本地具备 Blender 的 Python 环境，并希望验证 `executor` 的基本能力，可在 Blender 附带的 Python 中运行：

```bash
"$(which blender)" --background --python-expr "import pytest, sys; sys.exit(pytest.main(['addons/ai_modeler/tests/test_executor_ops.py']))"
```

上述命令会在后台模式执行 pytest，当 Blender 不提供 `bpy` 时测试会自动跳过。

## 常见问题与排查

| 症状 | 可能原因 | 解决方式 |
| ---- | -------- | -------- |
| 面板无响应 / 无法生成模型 | 提示词为空或 Planner 返回异常 | 检查侧栏是否填写提示词，必要时查看系统控制台输出日志。 |
| 在线 Planner 调用失败 | 网络不可达或 API Key 错误 | 在插件偏好设置中确认 Base URL 与 API Key，或暂时移除配置以回退到离线规则 Planner。 |
| 导出失败 | 未选择导出路径或没有写权限 | 再次点击导出按钮并确认文件路径可写。 |
| 材质未正确应用 | 对象无几何数据或使用曲线等非 Mesh 类型 | 请确保对象为 Mesh，并在执行完布尔/阵列后仍保持几何可用。 |

## 接入在线 LLM Planner

插件提供简单的 HTTP 客户端，默认向 `{base_url}/plan` 发送如下 JSON：

```json
{
  "prompt": "中文或英文描述",
  "units": "M"
}
```

预期返回：

```json
{
  "id": "uuid",
  "prompt": "原始提示词",
  "units": "M",
  "steps": [
    {"op": "ADD_CUBE", "params": {"size": 1.0, "units": "M", "name": "MyCube"}},
    {"op": "SET_MATERIAL", "params": {"target": "MyCube", "preset": "metal_brushed"}}
  ]
}
```

将服务地址与 API Key 填写到 `Edit > Preferences > Add-ons > AI Modeler` 的偏好设置即可启用。客户端带有重试与超时机制，失败时会自动回退到离线规则 Planner。

## 许可协议

本项目基于 [MIT License](LICENSE) 开源，欢迎自由使用与二次开发。
