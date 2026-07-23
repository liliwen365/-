// 错误信息友好化：把后端返回的 traceback / 校验消息翻译成用户看得懂的中文提示。
// 后端会原样透传两类文本：① validate_params 抛的 ValueError 消息（短句）
// ② 子进程 traceback.format_exc()（完整 Python 堆栈）。本工具对两者都做匹配。

export interface FriendlyError {
  title: string   // 一句话友好提示，给非技术用户看
  detail: string  // 原始技术详情，供"查看技术详情"
}

// 关键字 → 友好提示。按数组顺序从上到下匹配，先命中先用。
const RULES: Array<{ test: RegExp; title: string }> = [
  // 参数校验类（file-organizer validate_params 抛出的 ValueError）
  { test: /目标存放路径不能为空/, title: '任务清单里有"目标存放路径"未填的行，请补全或删除空行后再扫描' },
  { test: /任务ID不能为空/, title: '任务清单里有"任务ID"未填的行，请补全或删除空行后再扫描' },
  { test: /文件分类不能为空/, title: '规则设置里有"文件分类"未填，请打开「规则设置」补全' },
  { test: /源文件搜索路径不能为空/, title: '规则设置里有"搜索路径"未填，请打开「规则设置」补全' },
  { test: /文件名模式不能为空/, title: '规则设置里有"文件名模式"未填，请打开「规则设置」补全' },

  // 业务前置类
  { test: /请先添加任务/, title: '任务清单为空，请先添加任务' },
  { test: /请先配置规则/, title: '还未配置规则，请先加载模板或手动配置规则' },

  // 文件系统类（traceback 里的异常类型或 file_scanner 的报错）
  { test: /FileNotFoundError|路径或模式为空/, title: '文件或目录不存在，请检查配置的路径是否还在、是否被移动' },
  { test: /PermissionError|Access is denied|拒绝访问/, title: '没有访问权限，请检查文件夹权限或是否被其他程序占用' },
  { test: /\[Errno 28\]|No space left|磁盘空间不足/, title: '磁盘空间不足，无法写入目标路径' },
  { test: /未找到匹配的文件/, title: '按当前规则没有找到匹配文件，请核对关键词和搜索路径' },
  { test: /复制失败/, title: '复制文件时失败，请检查目标盘是否可写、空间是否充足' },
  { test: /OSError|WinError/, title: '路径无法访问，请检查磁盘或网络盘是否连接正常' },

  // 依赖组件类
  { test: /pyodbc|xlwings|com_error|CoInitialize|pywintypes/, title: 'Excel 或数据库组件调用失败，可能是 Office 未安装或未激活' },
  { test: /ModuleNotFoundError|ImportError/, title: '缺少必要的依赖组件，请联系技术支持' },
]

export function friendlyError(raw: string): FriendlyError {
  const text = raw || ''
  for (const rule of RULES) {
    if (rule.test.test(text)) {
      return { title: rule.title, detail: text }
    }
  }
  // 兜底：长 traceback 取最后一行（通常是异常类型+消息）作 title，完整原文放 detail
  if (text.includes('Traceback')) {
    const lines = text.trim().split('\n').filter(l => l.trim())
    const lastLine = lines[lines.length - 1] || '执行失败'
    return { title: lastLine, detail: text }
  }
  return { title: text || '执行失败', detail: text }
}
