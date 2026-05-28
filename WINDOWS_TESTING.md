# Windows环境测试指南

## 快速测试（在Windows机器上）

### 前置条件

1. Windows 10/11 电脑
2. Python 3.13+ 安装
3. Git（可选）

### 测试步骤

#### 1. 克隆项目（如果在Windows上测试）

```powershell
git clone <项目路径>
cd 本地自动化平台
```

#### 2. 安装依赖

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-playwright pytest-asyncio
playwright install chromium
```

#### 3. 创建测试文件

```powershell
# 创建测试目录
mkdir test_files_win\source

# 创建中文文件名的测试文件
"测试发票内容" | Out-File -Encoding UTF8 test_files_win\source\ABC001发票.pdf
"测试报关单内容" | Out-File -Encoding UTF8 test_files_win\source\ABC001报关单.pdf
"测试装箱单内容" | Out-File -Encoding UTF8 test_files_win\source\ABC001装箱单.pdf
```

#### 4. 运行测试

```powershell
# 运行所有测试
pytest -v

# 只运行Windows兼容性测试
pytest tests/test_windows_compatibility.py -v

# 运行文件扫描测试
pytest tests/test_file_scanner.py -v
```

## 关键测试点

### 1. 路径格式

| 场景 | 路径格式 | 预期行为 |
|------|---------|---------|
| 本地磁盘 | `C:\path\to\files` | ✓ 正常工作 |
| 网络驱动器映射 | `Y:\报关单\2026年\*.pdf` | ✓ 需验证 |
| UNC路径 | `\\NAS-Server\退税资料\*.pdf` | ✓ 需验证 |
| 相对路径 | `.\source\*.pdf` | ✓ 需验证 |

### 2. 中文字符

- 文件名：`ABC001发票.pdf` ✓
- 目录名：`报关单\2026年` ✓
- 路径含空格：`C:\My Documents\退税资料\*.pdf` ✓

### 3. 文件名匹配

- Windows `fnmatch` **不区分大小写**：`*.PDF` 匹配 `test.pdf`
- macOS/Linux **区分大小写**：`*.PDF` 不匹配 `test.pdf`

## 常见问题

### 问题1：网络驱动器无法访问

**症状**：扫描 `Y:\` 路径时提示"路径不存在"

**原因**：网络驱动器未连接或映射断开

**解决**：
```powershell
# 检查网络驱动器连接
net use

# 重新映射网络驱动器
net use Y: \\NAS-Server\退税资料 /persistent:yes
```

### 问题2：中文文件名乱码

**症状**：中文文件名显示为乱码或找不到

**原因**：文件编码问题

**解决**：确保文件使用UTF-8编码保存
```powershell
# 使用UTF-8编码创建文件
"内容" | Out-File -Encoding UTF8 "中文文件名.pdf"
```

### 问题3：权限不足

**症状**：`PermissionError` 或 `OSError: [Errno 13]`

**原因**：网络驱动器权限不足

**解决**：
```powershell
# 检查目录权限
icacls "Y:\报关单"

# 以管理员身份运行PowerShell
# 右键PowerShell → "以管理员身份运行"
```

## 自动化测试（推荐）

### 使用GitHub Actions（无需本地Windows机器）

1. 将代码推送到GitHub
2. 查看Actions标签页的"Test on Windows"工作流
3. 自动在Windows环境中运行所有测试

### 使用Docker（需要在macOS/Linux上模拟Windows）

```bash
# 拉取Windows镜像
docker pull mcr.microsoft.com/windows/nanoserver:ltsc2022

# 运行Windows容器（实验性）
docker run --rm -v $(pwd):C:\app mcr.microsoft.com/windows/nanoserver:ltsc2022
```

## 验证清单

在Windows环境测试时，验证以下功能：

- [ ] 本地磁盘路径扫描（`C:\path\*.pdf`）
- [ ] 网络驱动器扫描（`Y:\报关单\*.pdf`）
- [ ] UNC路径扫描（`\\Server\Share\*.pdf`）
- [ ] 中文文件名正确处理
- [ ] 含空格路径正确处理
- [ ] 子目录递归扫描
- [ ] 文件名大小写匹配（Windows不区分）
- [ ] E2E测试完整流程

## 报告问题

如果Windows测试失败，报告时请包含：

1. Windows版本（`winver`）
2. Python版本（`python --version`）
3. 错误信息和堆栈跟踪
4. 复现步骤
5. 测试文件结构（`tree /F` 命令输出）
