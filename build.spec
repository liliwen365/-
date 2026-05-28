# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 — onedir 模式，Windows 生产部署。"""
import sys
import os

block_cipher = None

# 前端 dist 和内置插件作为只读资源嵌入
datas = [
    ('frontend/dist', 'frontend/dist'),
    ('plugins', 'plugins'),
    ('assets/icon.ico', 'assets'),
    ('assets/icon.png', 'assets'),
]

# PyInstaller 静态分析无法发现的动态导入
hiddenimports = [
    # uvicorn 全套（字符串导入 "backend.app:app" 触发）
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    # backend 所有路由和模块
    'backend.app',
    'backend.config',
    'backend.database',
    'backend.logger',
    'backend.auth',
    'backend.plugin_manager',
    'backend.plugin_sdk',
    'backend.ws_manager',
    'backend.scheduler',
    'backend.task_runner',
    'backend.routes.system',
    'backend.routes.plugins',
    'backend.routes.auth',
    'backend.routes.schedules',
    'backend.routes.ws',
    'backend.utils.tray',
    'backend.utils.resource_path',
    'backend.capabilities.file_scanner',
    'backend.capabilities.file_ops',
    'backend.capabilities.template_engine',
    'backend.capabilities.progress',
    'backend.capabilities.matcher',
    'backend.capabilities.excel_reader',
    # pydantic / anyio / http
    'pydantic_settings',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'httpcore',
    'httptools',
    # pystray Windows 后端
    'pystray._win32',
    # 插件 engine + rules
    'engine',
    'rules',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pkg_resources'],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LocalAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LocalAgent',
)
