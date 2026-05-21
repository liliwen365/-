# -*- coding: utf-8 -*-
"""插件SDK — 基于pluggy的钩子规范。插件只需依赖此模块的hookimpl装饰器。"""
import pluggy

hookspec = pluggy.HookspecMarker("localagent")
hookimpl = pluggy.HookimplMarker("localagent")


class LocalAgentSpec:
    """平台定义的插件钩子规范。所有插件通过hookimpl实现这些钩子。"""

    @hookspec
    def get_plugin_info(self) -> dict:
        """返回插件元信息。"""
        ...

    @hookspec
    def validate_params(self, params: dict) -> dict:
        """校验用户提交的参数，返回清洗后的参数。"""
        ...

    @hookspec
    def execute(self, params: dict, progress_callback=None) -> dict:
        """执行插件核心逻辑。

        Args:
            params: 用户配置的参数（已校验）
            progress_callback: callback(current, total, message)
        Returns:
            {"status": "success"/"error", "summary": "...", "data": {...}}
        """
        ...

    @hookspec
    def on_load(self):
        """插件被加载时调用（可选）。"""
        pass

    @hookspec
    def on_unload(self):
        """插件被卸载时调用（可选）。"""
        pass
