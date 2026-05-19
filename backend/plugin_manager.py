# -*- coding: utf-8 -*-
"""插件管理器 - 发现/注册/加载/执行。"""
import os
import importlib
import yaml

from backend.base_plugin import BasePlugin
from backend.database import SessionLocal, PluginModel
from backend.logger import logger
from backend.config import settings


class PluginManager:
    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}

    def discover_plugins(self):
        """扫描插件目录，发现并加载所有插件。"""
        dirs = []
        if os.path.isdir(settings.PLUGINS_DIR):
            dirs.append(settings.PLUGINS_DIR)
        os.makedirs(settings.USER_PLUGINS_DIR, exist_ok=True)
        dirs.append(settings.USER_PLUGINS_DIR)

        for base_dir in dirs:
            for name in os.listdir(base_dir):
                plugin_dir = os.path.join(base_dir, name)
                manifest_path = os.path.join(plugin_dir, "plugin.yaml")
                if not os.path.isdir(plugin_dir) or not os.path.exists(manifest_path):
                    continue
                try:
                    self._load_plugin(plugin_dir, manifest_path)
                except Exception as e:
                    logger.error(f"加载插件 {name} 失败: {e}")

        logger.info(f"已加载 {len(self._plugins)} 个插件: {list(self._plugins.keys())}")

    def _load_plugin(self, plugin_dir: str, manifest_path: str):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)

        name = manifest.get("name")
        if not name:
            raise ValueError("plugin.yaml 缺少 name 字段")
        if name in self._plugins:
            return

        entry = manifest.get("entry", "")
        if ":" not in entry:
            raise ValueError(f"entry 格式错误，应为 'module:ClassName'，实际: {entry}")

        module_path, class_name = entry.split(":", 1)

        # 将插件目录加入sys.path以便import
        import sys
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)

        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)

        if not issubclass(plugin_class, BasePlugin):
            raise TypeError(f"{class_name} 未继承 BasePlugin")

        instance = plugin_class()
        instance.plugin_dir = plugin_dir
        instance.manifest = manifest
        instance.on_load()

        self._plugins[name] = instance

        # 同步到数据库
        self._register_to_db(manifest)

    def _register_to_db(self, manifest: dict):
        db = SessionLocal()
        try:
            name = manifest.get("name")
            existing = db.query(PluginModel).filter(PluginModel.name == name).first()
            if not existing:
                db.add(PluginModel(
                    name=name,
                    display_name=manifest.get("display_name", name),
                    version=manifest.get("version", "0.0.0"),
                    description=manifest.get("description", ""),
                    category=manifest.get("category", "custom"),
                    icon=manifest.get("icon", ""),
                    color=manifest.get("color", "#2196F3"),
                    author=manifest.get("author", ""),
                ))
                db.commit()
        finally:
            db.close()

    def get_plugin(self, name: str) -> BasePlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        return [p.get_info() for p in self._plugins.values()]

    def cleanup(self):
        for p in self._plugins.values():
            try:
                p.on_unload()
            except Exception:
                pass
