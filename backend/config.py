# -*- coding: utf-8 -*-
"""配置管理 - Pydantic Settings + 环境变量。"""

import os
import platform
import secrets
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "本地自动化平台"
    APP_VERSION: str = "0.1.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8088
    DEBUG: bool = False

    # 执行过程控制（.env 可覆盖，前缀 LOCAL_AGENT_）
    TASK_TIMEOUT_SEC: int = 600     # 单任务最长执行秒数，超时强杀
    SCAN_MAX_FILES: int = 50000     # 单次扫描最多收集文件数，防 OOM/无限递归
    SCAN_MAX_DEPTH: int = 10        # os.walk 最大递归深度

    IS_WINDOWS: bool = platform.system() == "Windows"
    IS_MAC: bool = platform.system() == "Darwin"

    # 数据目录
    if IS_WINDOWS:
        DATA_DIR: str = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME
        )
    elif IS_MAC:
        DATA_DIR: str = os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", APP_NAME
        )
    else:
        DATA_DIR: str = os.path.join(os.path.expanduser("~"), f".localagent")

    DB_PATH: Optional[str] = None
    PLUGINS_DIR: str = ""
    USER_PLUGINS_DIR: str = ""
    API_TOKEN: str = ""

    model_config = {"env_prefix": "LOCAL_AGENT_", "env_file": ".env"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        os.makedirs(self.DATA_DIR, exist_ok=True)
        if not self.DB_PATH:
            self.DB_PATH = os.path.join(self.DATA_DIR, "localagent.db")
        if not self.PLUGINS_DIR:
            if getattr(__import__("sys"), "frozen", False):
                self.PLUGINS_DIR = os.path.join(__import__("sys")._MEIPASS, "plugins")
            else:
                self.PLUGINS_DIR = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "plugins"
                )
        if not self.USER_PLUGINS_DIR:
            self.USER_PLUGINS_DIR = os.path.join(self.DATA_DIR, "user-plugins")
        self._init_api_token()

    def _init_api_token(self):
        token_path = os.path.join(self.DATA_DIR, ".api_token")
        if os.path.exists(token_path):
            with open(token_path, "r") as f:
                self.API_TOKEN = f.read().strip()
        if not self.API_TOKEN:
            self.API_TOKEN = secrets.token_hex(32)
            with open(token_path, "w") as f:
                f.write(self.API_TOKEN)


settings = Settings()
