# -*- coding: utf-8 -*-
"""一键构建脚本 — 在 Windows 上运行，产出安装包。

流程：安装前端依赖 → 构建前端 → PyInstaller 打包 → Inno Setup 安装包

用法:
    python build.py           # 完整构建
    python build.py --skip-npm  # 跳过前端构建（已构建过）
    python build.py --skip-iss  # 跳过 Inno Setup
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd, cwd=None):
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or ROOT)
    if result.returncode != 0:
        print(f"[FAIL] 命令失败: {cmd}")
        sys.exit(1)


def main():
    skip_npm = "--skip-npm" in sys.argv
    skip_iss = "--skip-iss" in sys.argv

    print("=" * 50)
    print("  LocalAgent 构建工具")
    print("=" * 50)

    # 1. 前端构建
    if not skip_npm:
        print("\n[1/4] 构建前端...")
        frontend = ROOT / "frontend"
        if not (frontend / "node_modules").exists():
            run("npm install", cwd=frontend)
        run("npm run build", cwd=frontend)
    else:
        print("\n[1/4] 跳过前端构建（--skip-npm）")

    # 2. 确认前端产物
    dist_dir = ROOT / "frontend" / "dist"
    if not dist_dir.exists():
        print(f"[FAIL] 前端产物不存在: {dist_dir}")
        print("请先运行: cd frontend && npm install && npm run build")
        sys.exit(1)
    print(f"  前端产物: {dist_dir}")

    # 3. PyInstaller 打包
    print("\n[2/4] PyInstaller 打包...")
    run("pyinstaller build.spec --clean --noconfirm")

    exe_path = ROOT / "dist" / "LocalAgent" / "LocalAgent.exe"
    if not exe_path.exists():
        print(f"[FAIL] 打包产物不存在: {exe_path}")
        sys.exit(1)
    print(f"  打包产物: {exe_path}")

    # 4. Inno Setup 安装包
    if not skip_iss:
        print("\n[3/4] 生成安装包...")
        iss_path = ROOT / "setup.iss"
        iscc = shutil.which("ISCC") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if not os.path.exists(iscc):
            print(f"  [SKIP] 未找到 Inno Setup: {iscc}")
            print("  安装 Inno Setup 6: https://jrsoftware.org/isdl.php")
        else:
            run(f'"{iscc}" "{iss_path}"')
    else:
        print("\n[3/4] 跳过安装包（--skip-iss）")

    print("\n[4/4] 完成!")
    print(f"  exe 目录: {ROOT / 'dist' / 'LocalAgent'}")
    print(f"  安装包:   {ROOT / 'dist' / 'LocalAgent-Setup.exe'}")
    print("=" * 50)


if __name__ == "__main__":
    main()
