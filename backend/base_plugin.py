# -*- coding: utf-8 -*-
"""插件基类 - 所有插件必须继承。"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class BasePlugin(ABC):
    """插件基类。每个插件目录需包含plugin.yaml和实现此基类的Python类。"""

    plugin_dir: str = ""
    manifest: dict = {}

    def get_info(self) -> dict:
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

    @abstractmethod
    def validate_params(self, params: dict) -> dict:
        """校验用户参数，返回清洗后的参数。"""
        ...

    @abstractmethod
    def execute(self, params: dict, progress_callback: Optional[Callable] = None) -> dict:
        """执行插件核心逻辑。

        Args:
            params: 用户配置的参数（已校验）
            progress_callback: callback(current, total, message)
        Returns:
            {"status": "success"/"error", "summary": "...", "data": {...}}
        """
        ...

    def on_load(self):
        pass

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
