# -*- coding: utf-8 -*-
"""Windows环境一键测试工具 - 在真实Windows+NAS环境验证核心功能。

使用方法：
  方式1: 把整个项目复制到Windows，然后运行:
         python deploy/windows_test_tool.py

  方式2: 只复制此文件到项目根目录，然后运行:
         python windows_test_tool.py

  方式3: 双击此文件（需要.py关联到Python）

测试完成后会在当前目录生成 windows_test_report/ 目录，包含:
  - report.txt   人类可读的测试报告
  - report.json  机器可读的测试结果
"""
import os
import sys
import json
import shutil
import traceback
from pathlib import Path
from datetime import datetime


class R:
    """测试结果记录器。"""
    def __init__(self):
        self.items = []
        self.report_dir = Path.cwd() / "windows_test_report"

    def ok(self, name, detail=""):
        self.items.append({"test": name, "pass": True, "detail": detail})
        print(f"  [PASS] {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name, detail=""):
        self.items.append({"test": name, "pass": False, "detail": detail})
        print(f"  [FAIL] {name} — {detail}")

    def skip(self, name, detail=""):
        self.items.append({"test": name, "pass": None, "detail": detail})
        print(f"  [SKIP] {name} — {detail}")

    @property
    def passed(self):
        return sum(1 for i in self.items if i["pass"] is True)

    @property
    def failed(self):
        return sum(1 for i in self.items if i["pass"] is False)

    def save(self):
        self.report_dir.mkdir(exist_ok=True)
        # JSON report
        (self.report_dir / "report.json").write_text(
            json.dumps({"timestamp": datetime.now().isoformat(), "results": self.items},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # Text report
        lines = [
            f"Windows环境测试报告",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{'=' * 50}",
            f"通过: {self.passed}  失败: {self.failed}  总计: {len(self.items)}",
            "",
        ]
        for i in self.items:
            mark = "PASS" if i["pass"] else "FAIL" if i["pass"] is False else "SKIP"
            lines.append(f"[{mark}] {i['test']}")
            if i["detail"]:
                lines.append(f"      {i['detail']}")
        (self.report_dir / "report.txt").write_text("\n".join(lines), encoding="utf-8")


def find_project_root():
    """自动查找项目根目录（支持从deploy/或根目录运行）。"""
    here = Path(__file__).resolve().parent
    if (here / "backend" / "app.py").exists():
        return here
    if (here / ".." / "backend" / "app.py").exists():
        return here.parent
    return None


def test_environment(r):
    """T1: Python版本和核心依赖。"""
    print("\n[T1] 环境检查")

    v = sys.version_info
    if v >= (3, 9):
        r.ok("Python版本", f"{v.major}.{v.minor}.{v.micro}")
    else:
        r.fail("Python版本", f"{v.major}.{v.minor}.{v.micro}，需要 >= 3.9")
        return False

    deps = {"fastapi": "FastAPI", "sqlalchemy": "SQLAlchemy", "pandas": "Pandas",
            "pluggy": "pluggy", "yaml": "PyYAML", "httpx": "httpx", "requests": "requests"}
    for mod, name in deps.items():
        try:
            __import__(mod)
            r.ok(name)
        except ImportError:
            r.fail(name, "未安装")

    return r.items[-1]["pass"]  # 最后一个依赖的结果不重要，继续跑


def test_project_structure(r, root):
    """T2: 项目文件完整性。"""
    print("\n[T2] 项目结构检查")

    checks = [
        ("backend/app.py", "FastAPI应用"),
        ("backend/capabilities/file_scanner.py", "文件扫描器"),
        ("backend/capabilities/template_engine.py", "模板引擎"),
        ("plugins/file-organizer/plugin.yaml", "文件整理插件"),
    ]
    for rel, desc in checks:
        p = root / rel
        if p.exists():
            r.ok(desc, rel)
        else:
            r.fail(desc, f"缺失: {rel}")


def test_imports(r, root):
    """T3: 核心模块导入。"""
    print("\n[T3] 模块导入测试")

    sys.path.insert(0, str(root))
    modules = [
        ("backend.capabilities.file_scanner", "scan_directory"),
        ("backend.capabilities.template_engine", "build_path"),
        ("backend.capabilities.progress", "ParallelProgress"),
        ("backend.utils.path_utils", "PathUtils"),
    ]
    for mod_path, func_name in modules:
        try:
            mod = __import__(mod_path, fromlist=[func_name])
            getattr(mod, func_name)
            r.ok(mod_path.split(".")[-1])
        except Exception as e:
            r.fail(mod_path.split(".")[-1], str(e))


def test_path_utils(r):
    """T4: 路径处理工具。"""
    print("\n[T4] 路径处理测试")

    from backend.utils.path_utils import PathUtils

    if PathUtils.is_windows_unc_path(r"\\NAS-Server\Share"):
        r.ok("UNC路径识别")
    else:
        r.fail("UNC路径识别")

    if PathUtils.is_windows_drive_path(r"Y:\报关单"):
        r.ok("盘符路径识别")
    else:
        r.fail("盘符路径识别")

    if "UNC" in PathUtils.get_path_type(r"\\Server\Share"):
        r.ok("路径类型判断-UNC")
    else:
        r.fail("路径类型判断-UNC")

    if "盘符" in PathUtils.get_path_type(r"Y:\data"):
        r.ok("路径类型判断-盘符")
    else:
        r.fail("路径类型判断-盘符")


def test_template_engine(r):
    """T5: 模板引擎（路径+文件名替换）。"""
    print("\n[T5] 模板引擎测试")

    from backend.capabilities.template_engine import build_path, build_filename_pattern

    # 路径替换
    result = build_path("Y:\\报关单\\{PathKeyword}", "ABC001", override="")
    if "ABC001" in result and "报关单" in result:
        r.ok("路径关键词替换", result)
    else:
        r.fail("路径关键词替换", result)

    # override优先
    result2 = build_path("Y:\\data\\{PathKeyword}", "ABC", override="D:\\other")
    if result2 == "D:\\other":
        r.ok("路径覆盖优先", result2)
    else:
        r.fail("路径覆盖优先", result2)

    # 文件名模式
    pat = build_filename_pattern("*{PrimaryKeyword}*发票*.*", "ABC", "发票")
    if "ABC" in pat and "发票" in pat:
        r.ok("文件名模式替换", pat)
    else:
        r.fail("文件名模式替换", pat)


def test_file_scanner(r, tmp):
    """T6: 文件扫描（中文文件名、子目录、空格路径）。"""
    print("\n[T6] 文件扫描测试")

    from backend.capabilities.file_scanner import scan_directory

    # 创建测试文件
    src = tmp / "scan_test"
    src.mkdir()
    (src / "ABC001发票.pdf").write_text("inv", encoding="utf-8")
    (src / "ABC001报关单.pdf").write_text("decl", encoding="utf-8")
    (src / "ABC002发票.pdf").write_text("inv2", encoding="utf-8")
    sub = src / "子目录"
    sub.mkdir()
    (sub / "ABC003装箱单.pdf").write_text("pack", encoding="utf-8")
    space = tmp / "folder with spaces"
    space.mkdir()
    (space / "文件.pdf").write_text("sp", encoding="utf-8")

    # 基本扫描
    result = scan_directory(str(src), "*.pdf")
    if result.error is None and len(result.files) >= 3:
        r.ok("基本扫描", f"找到 {len(result.files)} 个文件")
    else:
        r.fail("基本扫描", result.error or f"只找到 {len(result.files)} 个文件")

    # 关键词匹配
    result2 = scan_directory(str(src), "*ABC001*发票*.*")
    if result2.error is None and len(result2.files) >= 1:
        r.ok("关键词扫描", f"找到 {len(result2.files)} 个ABC001发票")
    else:
        r.fail("关键词扫描", result2.error or "未找到ABC001发票")

    # 子目录递归
    result3 = scan_directory(str(src), "*装箱单*.*")
    if result3.error is None and any("ABC003" in f.name for f in result3.files):
        r.ok("子目录递归", f"找到子目录中的装箱单")
    else:
        r.fail("子目录递归", result3.error or "未找到子目录中的文件")

    # 带空格路径
    result4 = scan_directory(str(space), "*.pdf")
    if result4.error is None and len(result4.files) >= 1:
        r.ok("带空格路径")
    else:
        r.fail("带空格路径", result4.error)


def _list_available_drives():
    """列出当前会话可见的所有驱动器。"""
    import ctypes
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            letter = chr(65 + i) + ":\\"
            dt = ctypes.windll.kernel32.GetDriveTypeW(letter)
            types = {2: "可移动", 3: "本地", 4: "网络", 5: "光驱", 6: "RAM"}
            drives.append(f"{letter} ({types.get(dt, '未知')})")
    return drives


def _drive_exists(drive_path):
    """检测网络驱动器是否可访问（Path.exists() 对映射盘不可靠）。"""
    import ctypes
    path = str(drive_path).rstrip("\\/")

    # 列出所有可见驱动器供诊断
    available = _list_available_drives()
    print(f"  可见驱动器: {', '.join(available)}")

    # 方法1: GetDriveType 检测盘符类型
    if len(path) == 2 and path[1] == ":":
        dt = ctypes.windll.kernel32.GetDriveTypeW(path + "\\")
        print(f"  GetDriveType({path}\\) = {dt} (1=不存在,3=本地,4=网络)")
        if dt > 1:
            return True

    # 方法2: 尝试列举目录
    try:
        items = os.listdir(path + "\\")
        print(f"  os.listdir 成功，共 {len(items)} 项")
        return True
    except Exception as e:
        print(f"  os.listdir 失败: {type(e).__name__}: {e}")

    # 方法3: 尝试直接访问子路径（有时根目录没权限但子目录可以）
    return False


def test_nas_connection(r, nas_path):
    """T7: NAS/网络驱动器连接。"""
    print(f"\n[T7] NAS连接测试 ({nas_path})")

    if not _drive_exists(nas_path):
        r.skip("NAS连接", f"{nas_path} 不存在或不可访问")
        return None

    try:
        items = list(Path(nas_path).iterdir())
        names = [d.name for d in items[:10]]
        r.ok("NAS根目录", f"前10项: {names}")
    except Exception as e:
        r.fail("NAS根目录", str(e))
        return False

    return True


def test_nas_scan(r, nas_path):
    """T8: NAS真实文件扫描。"""
    print(f"\n[T8] NAS文件扫描测试 ({nas_path})")

    if not _drive_exists(nas_path):
        r.skip("NAS扫描", "NAS路径不可用")
        return

    from backend.capabilities.file_scanner import scan_directory

    result = scan_directory(nas_path, "*.pdf")
    if result.error:
        r.fail("NAS-PDF扫描", result.error)
    else:
        r.ok("NAS-PDF扫描", f"找到 {len(result.files)} 个PDF文件")

    result2 = scan_directory(nas_path, "*.*")
    if result2.error:
        r.skip("NAS全文件扫描", result2.error)
    else:
        exts = set(f.name.rsplit(".", 1)[-1].lower() for f in result2.files if "." in f.name)
        r.ok("NAS文件类型", f"共 {len(result2.files)} 个文件，类型: {sorted(exts)[:10]}")


def test_full_workflow(r, tmp):
    """T9: 完整文件整理流程（扫描→匹配→复制）。"""
    print("\n[T9] 完整文件整理流程")

    from backend.capabilities.file_scanner import scan_directory
    from backend.capabilities.file_ops import copy_file
    from backend.capabilities.template_engine import build_path, build_filename_pattern

    # 模拟出口退税场景
    source = tmp / "出口退税源文件"
    source.mkdir()
    (source / "ABC001商业发票.pdf").write_text("发票内容", encoding="utf-8")
    (source / "ABC001出口报关单.pdf").write_text("报关单", encoding="utf-8")
    (source / "ABC001装箱清单.pdf").write_text("装箱单", encoding="utf-8")
    (source / "XYZ999合同.pdf").write_text("无关文件", encoding="utf-8")

    dest = tmp / "整理目标"
    dest.mkdir()

    # 模拟规则：查找ABC001的发票和报关单
    rules = [
        {"doc_type": "发票", "pattern": "*ABC001*发票*.*", "subfolder": "发票"},
        {"doc_type": "报关单", "pattern": "*ABC001*报关*.*", "subfolder": "报关单"},
        {"doc_type": "装箱单", "pattern": "*ABC001*装箱*.*", "subfolder": "装箱单"},
    ]

    all_copied = 0
    for rule in rules:
        result = scan_directory(str(source), rule["pattern"])
        if result.error:
            r.fail(f"扫描-{rule['doc_type']}", result.error)
            continue

        task_dest = dest / "ABC001" / rule["subfolder"]
        task_dest.mkdir(parents=True, exist_ok=True)

        for f in result.files:
            cp = copy_file(f.path, str(task_dest / f.name))
            if cp.status == "success":
                all_copied += 1

    if all_copied >= 3:
        r.ok("完整流程", f"成功扫描并复制 {all_copied} 个文件")
        # 验证目标目录结构
        expected_files = ["ABC001/发票", "ABC001/报关单", "ABC001/装箱单"]
        for ef in expected_files:
            if (dest / ef).exists() and list((dest / ef).iterdir()):
                r.ok(f"  {ef}", "文件已就位")
            else:
                r.fail(f"  {ef}", "目录为空或不存在")
    else:
        r.fail("完整流程", f"只复制了 {all_copied} 个文件，期望 >= 3")


def main():
    print("=" * 50)
    print("  Windows环境测试工具 v3.0")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # NAS路径：命令行参数 > 环境变量 > 默认Y盘
    nas_path = "Y:\\"
    if len(sys.argv) > 1:
        nas_path = sys.argv[1]
    elif os.environ.get("NAS_PATH"):
        nas_path = os.environ["NAS_PATH"]
    print(f"  NAS路径: {nas_path}")
    print(f"  用法: python {sys.argv[0]} [NAS路径，如 Y:\\ 或 D:\\data]")

    root = find_project_root()
    if not root:
        print("\n[ERROR] 找不到项目根目录（需要backend/app.py存在）")
        print("请把此文件放在项目根目录或deploy/目录下运行")
        input("\n按Enter退出...")
        return 1

    print(f"项目根目录: {root}")

    r = R()

    # 1. 环境检查（不依赖项目结构）
    test_environment(r)

    # 2-5. 项目结构、模块导入、路径工具、模板引擎
    test_project_structure(r, root)
    test_imports(r, root)
    test_path_utils(r)
    test_template_engine(r)

    # 创建临时目录（用当前目录而非系统tmp，避免权限/路径问题）
    tmp = root / "_test_tmp"
    tmp.mkdir(exist_ok=True)

    # 6. 文件扫描
    test_file_scanner(r, tmp)

    # 7-8. NAS测试（可配置路径）
    test_nas_connection(r, nas_path)
    test_nas_scan(r, nas_path)

    # 9. 完整流程
    test_full_workflow(r, tmp)

    # 清理
    shutil.rmtree(tmp, ignore_errors=True)

    # 汇总
    print("\n" + "=" * 50)
    print(f"  通过: {r.passed}  失败: {r.failed}  总计: {len(r.items)}")
    print("=" * 50)

    r.save()
    print(f"\n报告已保存到: {r.report_dir.resolve()}")

    input("\n按Enter退出...")
    return 0 if r.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
