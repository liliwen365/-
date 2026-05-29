# -*- coding: utf-8 -*-
"""插件管理器 — 发现/注册/加载。基于pluggy钩子系统。"""
import os
import sys
import importlib
import importlib.util
import traceback
import yaml

import pluggy

from backend.plugin_sdk import LocalAgentSpec, hookimpl
from backend.database import SessionLocal, PluginModel
from backend.logger import logger
from backend.config import settings


class PluginManifest:
    """持有plugin.yaml元数据的包装对象，支持hookimpl协议。"""

    def __init__(self, manifest: dict, plugin_dir: str):
        self.manifest = manifest
        self.plugin_dir = plugin_dir

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

    def get_template(self, template_name: str) -> dict | None:
        for t in self.manifest.get("templates", []):
            if t.get("name") == template_name:
                import json
                path = os.path.join(self.plugin_dir, t.get("file", ""))
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
        return None


class PluginManager:
    def __init__(self):
        self._pm = pluggy.PluginManager("localagent")
        self._pm.add_hookspecs(LocalAgentSpec)
        self._plugins: dict[str, object] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._load_errors: list[str] = []

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
                    err = f"加载插件 {name} 失败: {e}\n{traceback.format_exc()}"
                    logger.error(err)
                    self._load_errors.append(err)

        logger.info(f"已加载 {len(self._plugins)} 个插件: {list(self._plugins.keys())}")

    def _load_plugin(self, plugin_dir: str, manifest_path: str):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)

        name = manifest.get("name")
        if not name:
            raise ValueError("plugin.yaml 缺少 name 字段")
        if name in self._plugins:
            return

        mf = PluginManifest(manifest, plugin_dir)
        self._manifests[name] = mf

        entry = manifest.get("entry", "")
        if ":" not in entry:
            raise ValueError(f"entry 格式错误，应为 'module:ClassName'，实际: {entry}")

        module_path, class_name = entry.split(":", 1)

        # —— 模块隔离策略 ——
        # 每个插件的 engine.py / rules.py 等同名模块会互相冲突，
        # 所以加载前清理裸名，加载后把裸名移到命名空间名下。
        bare_names = ['engine', 'rules', module_path]
        saved = {}
        for bare in bare_names:
            if bare in sys.modules:
                saved[bare] = sys.modules.pop(bare)

        # 清理上次同名插件的命名空间残留（重新加载场景）
        ns_prefix = f'_plugin_{name}.'
        for k in list(sys.modules):
            if k.startswith(ns_prefix):
                sys.modules.pop(k)

        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)

        # 加载入口模块
        module_file = os.path.join(plugin_dir, f"{module_path}.py")
        namespaced = f'_plugin_{name}.{module_path}'

        spec = importlib.util.spec_from_file_location(namespaced, module_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[namespaced] = module

        try:
            spec.loader.exec_module(module)
        except Exception:
            # 加载失败：恢复之前保存的模块
            for bare, mod in saved.items():
                sys.modules[bare] = mod
            raise

        # 加载成功后：把 import chain 产生的裸名模块移到命名空间下
        for bare in ['engine', 'rules']:
            if bare in sys.modules:
                sys.modules[f'_plugin_{name}.{bare}'] = sys.modules[bare]
                del sys.modules[bare]

        plugin_class = getattr(module, class_name)

        instance = plugin_class()
        instance.plugin_dir = plugin_dir
        instance.manifest = manifest

        self._pm.register(instance, name=name)
        self._plugins[name] = instance

        self._pm.hook.on_load(plugin=instance)

        self._register_to_db(manifest)

        logger.debug(f"插件 {name} 加载成功，模块: {sorted(k for k in sys.modules if k.startswith(ns_prefix))}")

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

    def get_plugin(self, name: str):
        """返回插件实例，附带manifest和plugin_dir属性。"""
        return self._plugins.get(name)

    def get_manifest(self, name: str) -> PluginManifest | None:
        return self._manifests.get(name)

    def list_plugins(self) -> list[dict]:
        result = []
        for name, _ in self._plugins.items():
            mf = self._manifests.get(name)
            if mf:
                result.append(mf.get_info())
        return result

    def cleanup(self):
        for p in self._plugins.values():
            try:
                self._pm.hook.on_unload(plugin=p)
            except Exception:
                pass
