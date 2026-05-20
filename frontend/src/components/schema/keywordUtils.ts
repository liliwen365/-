/**
 * 紧凑格式 ↔ keyword-map dict 双向转换
 *
 * 紧凑格式: 分类:路径关键词|文件关键词;分类:路径关键词|文件关键词
 * - 路径关键词和文件关键词用 | 分隔
 * - 无 | 时默认为文件关键词（兼容旧格式 分类:关键词）
 * - 多个关键词用逗号分隔
 * - 输入 . 匹配所有
 *
 * 示例:
 *   采购合同:.|.              → { 采购合同: { path: ["."], file: ["."] } }
 *   发票:202603批次|26432000000695401411 → { 发票: { path: ["202603批次"], file: ["26432000000695401411"] } }
 *   发票:26432000000695401411 → { 发票: { path: [], file: ["26432000000695401411"] } }  (兼容旧格式)
 */

export function parseCompact(text: string): Record<string, { path: string[]; file: string[] }> {
  const result: Record<string, { path: string[]; file: string[] }> = {}
  if (!text.trim()) return result
  const pairs = text.split(';').filter(s => s.trim())
  for (const pair of pairs) {
    const colonIdx = pair.indexOf(':')
    if (colonIdx < 0) continue
    const dt = pair.substring(0, colonIdx).trim()
    const kwStr = pair.substring(colonIdx + 1).trim()
    if (!dt) continue

    let pathKws: string[] = []
    let fileKws: string[] = []

    if (kwStr.includes('|')) {
      const pipeIdx = kwStr.indexOf('|')
      const pathStr = kwStr.substring(0, pipeIdx).trim()
      const fileStr = kwStr.substring(pipeIdx + 1).trim()
      pathKws = pathStr ? pathStr.split(',').map(k => k.trim()).filter(k => k) : []
      fileKws = fileStr ? fileStr.split(',').map(k => k.trim()).filter(k => k) : []
    } else {
      fileKws = kwStr ? kwStr.split(',').map(k => k.trim()).filter(k => k) : []
    }

    result[dt] = { path: pathKws, file: fileKws }
  }
  return result
}

export function serializeCompact(
  data: Record<string, { path: string[]; file: string[] }>,
  docTypes: string[] = []
): string {
  const parts: string[] = []
  const orderedKeys = docTypes.length
    ? docTypes.filter(dt => data[dt])
    : Object.keys(data)
  for (const dt of orderedKeys) {
    const entry = data[dt]
    if (!entry) continue
    const hasPath = entry.path?.length
    const hasFile = entry.file?.length
    if (!hasPath && !hasFile) continue
    const pathStr = hasPath ? entry.path.join(',') : ''
    const fileStr = hasFile ? entry.file.join(',') : ''
    parts.push(`${dt}:${pathStr}|${fileStr}`)
  }
  return parts.join(';')
}
