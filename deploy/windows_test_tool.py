# -*- coding: utf-8 -*-
"""Windows环境一键测试工具 - 在真实Windows+NAS环境验证功能。

使用方法：
1. 将此文件复制到Windows机器
2. 双击运行：python windows_test_tool.py
3. 查看测试结果报告

测试内容：
- 环境检查（Python、依赖）
- NAS连接测试（Y盘访问）
- 文件扫描测试（真实路径）
- 规则模板验证
- 完整业务场景
"""
import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


class WindowsTester:
    """Windows环境测试器。"""

    def __init__(self):
        self.results = []
        self.test_dir = Path.cwd() / "windows_test_report"
        self.test_dir.mkdir(exist_ok=True)

    def add_result(self, test_name, success, detail=""):
        """记录测试结果。"""
        self.results.append({
            "test": test_name,
            "success": success,
            "detail": detail,
            "time": datetime.now().strftime("%H:%M:%S")
        })

    def test_environment(self):
        """测试1: 环境检查。"""
        print_info("测试1: 环境检查")
        try:
            # 检查Python版本
            version = sys.version_info
            if version.major >= 3 and version.minor >= 9:
                print_success(f"Python版本: {version.major}.{version.minor}.{version.micro}")
            else:
                print_error(f"Python版本过低: {version.major}.{version.minor}.{version.micro}")
                self.add_result("环境检查", False, f"Python版本过低")
                return

            # 检查依赖
            try:
                import fastapi
                import pandas
                print_success("依赖包检查: FastAPI, Pandas 已安装")
            except ImportError as e:
                print_error(f"依赖包缺失: {e}")
                self.add_result("环境检查", False, f"依赖缺失: {e}")
                return

            self.add_result("环境检查", True)
            print()

        except Exception as e:
            print_error(f"环境检查异常: {e}")
            self.add_result("环境检查", False, str(e))

    def test_nas_connection(self):
        """测试2: NAS连接测试。"""
        print_info("测试2: NAS连接测试")
        try:
            # 检查Y盘是否存在
            y_drive = Path("Y:\\")
            if y_drive.exists():
                print_success("Y盘可访问")
            else:
                print_warning("Y盘不存在或无法访问")
                self.add_result("NAS连接", False, "Y盘不存在")
                return

            # 列举Y盘根目录
            try:
                roots = list(y_drive.iterdir())[:5]  # 只列出前5个
                print_success(f"Y盘根目录内容（前5个）: {[d.name for d in roots]}")
            except Exception as e:
                print_error(f"无法列出Y盘内容: {e}")
                self.add_result("NAS连接", False, f"列表失败: {e}")
                return

            self.add_result("NAS连接", True)
            print()

        except Exception as e:
            print_error(f"NAS连接异常: {e}")
            self.add_result("NAS连接", False, str(e))

    def test_file_scanner(self):
        """测试3: 文件扫描功能。"""
        print_info("测试3: 文件扫描功能")
        try:
            # 导入file_scanner
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from backend.capabilities.file_scanner import scan_directory

            # 创建测试文件
            test_folder = Path.cwd() / "test_scan_files"
            test_folder.mkdir(exist_ok=True)
            (test_folder / "测试文件1.pdf").write_text("test")
            (test_folder / "测试文件2.pdf").write_text("test")

            # 测试扫描
            result = scan_directory(str(test_folder), "*.pdf")

            if result.error:
                print_error(f"扫描失败: {result.error}")
                self.add_result("文件扫描", False, result.error)
            else:
                print_success(f"扫描成功: 找到 {len(result.files)} 个文件")
                for f in result.files:
                    print(f"  - {f.name}")
                self.add_result("文件扫描", True)

            # 清理测试文件
            import shutil
            shutil.rmtree(test_folder, ignore_errors=True)
            print()

        except Exception as e:
            print_error(f"文件扫描异常: {e}")
            self.add_result("文件扫描", False, f"{e}\n{traceback.format_exc()}")

    def test_rule_template(self):
        """测试4: 规则模板验证。"""
        print_info("测试4: 规则模板验证")
        try:
            # 测试路径模板替换
            from backend.capabilities.template_engine import build_path, build_filename_pattern

            # 模拟Windows路径
            test_path = "Y:\\报关单\\2026年\\ABC001"
            result_path = build_path(test_path, "ABC", override="")

            if "ABC" in result_path:
                print_success(f"路径模板替换: {result_path}")
            else:
                print_error(f"路径模板替换失败: {result_path}")
                self.add_result("规则模板", False, "路径替换失败")
                return

            # 测试文件名模板
            pattern = build_filename_pattern("*{PrimaryKeyword}*发票*.*", "ABC", "发票")
            if "ABC" in pattern and "发票" in pattern:
                print_success(f"文件名模板: {pattern}")
            else:
                print_error(f"文件名模板失败: {pattern}")
                self.add_result("规则模板", False, "文件名模板失败")
                return

            self.add_result("规则模板", True)
            print()

        except Exception as e:
            print_error(f"规则模板异常: {e}")
            self.add_result("规则模板", False, f"{e}\n{traceback.format_exc()}")

    def test_chinese_encoding(self):
        """测试5: 中文编码测试。"""
        print_info("测试5: 中文编码测试")
        try:
            # 创建中文文件名
            test_file = Path.cwd() / "中文测试_发票.pdf"
            test_file.write_text("test content", encoding="utf-8")

            # 验证文件名
            if test_file.exists():
                print_success(f"中文文件名创建: {test_file.name}")
                self.add_result("中文编码", True)
            else:
                print_error("中文文件名创建失败")
                self.add_result("中文编码", False, "文件创建失败")

            # 清理
            test_file.unlink()
            print()

        except Exception as e:
            print_error(f"中文编码异常: {e}")
            self.add_result("中文编码", False, str(e))

    def test_real_business_scenario(self):
        """测试6: 真实业务场景（可选）。"""
        print_info("测试6: 真实业务场景")
        print_warning("此测试需要真实NAS路径，暂时跳过")
        print_warning("如需测试，请手动运行平台并扫描真实文件")
        self.add_result("真实业务场景", None, "需要真实NAS环境")
        print()

    def generate_report(self):
        """生成测试报告。"""
        print_info("生成测试报告")

        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = sum(1 for r in self.results if r['success'] is False)
        skipped = sum(1 for r in self.results if r['success'] is None)

        report_file = self.test_dir / "test_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"Windows环境测试报告\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"总计: {total} | 通过: {passed} | 失败: {failed} | 跳过: {skipped}\n\n")

            for r in self.results:
                status = "✓ 通过" if r['success'] else "✗ 失败" if r['success'] is False else "⊘ 跳过"
                f.write(f"{status} | {r['test']}\n")
                if r['detail']:
                    f.write(f"  详情: {r['detail']}\n")
                f.write("\n")

        print_success(f"报告已生成: {report_file}")
        print()

        # 输出总结
        print(f"{Colors.BLUE}{'='*50}{Colors.RESET}")
        print(f"{Colors.BLUE}测试总结{Colors.RESET}")
        print(f"  总计: {total}")
        print(f"  {Colors.GREEN}通过: {passed}{Colors.RESET}")
        if failed > 0:
            print(f"  {Colors.RED}失败: {failed}{Colors.RESET}")
        if skipped > 0:
            print(f"  {Colors.YELLOW}跳过: {skipped}{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*50}{Colors.RESET}")

        return failed == 0

    def run_all(self):
        """运行所有测试。"""
        print(f"{Colors.BLUE}{'='*50}{Colors.RESET}")
        print(f"{Colors.BLUE}Windows环境测试工具{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*50}{Colors.RESET}\n")

        self.test_environment()
        self.test_nas_connection()
        self.test_file_scanner()
        self.test_rule_template()
        self.test_chinese_encoding()
        self.test_real_business_scenario()

        return self.generate_report()


def main():
    """主函数。"""
    print("\n🚀 Windows环境测试工具启动\n")

    tester = WindowsTester()
    success = tester.run_all()

    # 生成JSON报告（供程序读取）
    json_report = tester.test_dir / "test_report.json"
    with open(json_report, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(tester.results),
            "passed": sum(1 for r in tester.results if r['success']),
            "failed": sum(1 for r in tester.results if r['success'] is False),
            "results": tester.results
        }, f, ensure_ascii=False, indent=2)

    print(f"\nJSON报告: {json_report}")
    print(f"文本报告: {tester.test_dir / 'test_report.txt'}")

    input("\n按Enter键退出...")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
