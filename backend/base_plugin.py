# -*- coding: utf-8 -*-
"""插件基类 — 便利抽象，内部用hookimpl注册到pluggy。"""
from typing import Callable, Optional

from backend.plugin_sdk import hookimpl


class BasePlugin:
    """插件基类。每个插件目录需包含plugin.yaml和实现此基类的Python类。
    通过hookimpl自动注册到pluggy钩子系统。"""

    plugin_dir: str = ""
    manifest: dict = {}

    @hookimpl
    def get_plugin_info(self) -> dict:
        return {
            "name": self.manifest.get("name", ""),
            "display_name": self.manifest.get("display_name", ""),
            "version": self.manifest.get("version", "0.0.0"),
            "description": self.manifest.get("description", ""),
            "category": self.manifest.get("category", "custom"),
            "icon": self.manifest.get("icon", ""),
            "color": self.manifest.get("color", "#2196F3"),
            "features": self.manifest.get("features", []),
            "params": self.manifest.get("params", []),
            "templates": self.manifest.get("templates", []),
        }

    @hookimpl
    def validate_params(self, params: dict) -> dict:
        return params

    @hookimpl
    def execute(self, params: dict, progress_callback: Optional[Callable] = None) -> dict:
        raise NotImplementedError

    @hookimpl
    def on_load(self):
        pass

    @hookimpl
    def on_unload(self):
        pass

    def get_template(self, template_name: str) -> Optional[dict]:
        for t in self.manifest.get("templates", []):
            if t.get("name") == template_name:
                import json, os
                path = os.path.join(self.plugin_dir, t.get("file", ""))
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
        return None
