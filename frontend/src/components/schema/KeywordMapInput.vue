<template>
  <div class="keyword-map-input">
    <!-- 模式切换 -->
    <div class="mode-switch">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button value="visual">可视化</el-radio-button>
        <el-radio-button value="text">文本模式</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 可视化模式 -->
    <template v-if="mode === 'visual'">
      <div class="usage-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>为每个文件分类设置关键词：输入文字后按回车添加标签。<b>路径关键词</b>用于替换搜索路径中的占位符，<b>文件关键词</b>用于匹配文件名。输入<b>.</b>表示匹配该路径下所有文件。</span>
      </div>
      <el-empty v-if="!docTypes.length" description="请先在「规则设置」中添加文件分类" :image-size="60" />
      <div v-for="dt in docTypes" :key="dt" class="keyword-group">
        <div class="group-header">
          <el-tag size="small" type="primary">{{ dt }}</el-tag>
        </div>
        <div class="group-fields">
          <div class="field-row">
            <span class="field-label">路径关键词</span>
            <el-select
              :model-value="getKeywords(dt, 'path')"
              @update:model-value="(val: string[]) => setKeywords(dt, 'path', val)"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="输入路径关键词后按回车，如：202603批次"
              size="small"
              style="flex: 1"
            />
          </div>
          <div class="field-row">
            <span class="field-label">文件关键词</span>
            <el-select
              :model-value="getKeywords(dt, 'file')"
              @update:model-value="(val: string[]) => setKeywords(dt, 'file', val)"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="输入文件关键词后按回车，如：ABC001（输入 . 匹配所有）"
              size="small"
              style="flex: 1"
            />
          </div>
        </div>
      </div>
    </template>

    <!-- 文本模式 -->
    <template v-if="mode === 'text'">
      <div class="usage-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>直接粘贴或编辑关键字文本。<b>格式：</b>分类:关键词1,关键词2;分类:关键词。<b>示例：</b><code>采购合同:.;销售合同:.;发票:26432000000695401411;报关单:报关单</code>。输入<b>.</b>匹配所有文件。多个关键词用逗号分隔。</span>
      </div>
      <el-input
        :model-value="compactText"
        @update:model-value="onCompactTextChange"
        type="textarea"
        :rows="6"
        placeholder="采购合同:.;销售合同:.;发票:26432000000695401411;报关单:报关单"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: Record<string, { path: string[]; file: string[] }>
  docTypes: string[]
}>()
const emit = defineEmits(['update:modelValue'])

const mode = ref<'visual' | 'text'>('visual')

// 紧凑格式 → keyword-map dict
// 格式: 分类:关键词1,关键词2;分类:关键词
// 关键词只填入 file 数组（兼容旧Excel格式）
function parseCompact(text: string): Record<string, { path: string[]; file: string[] }> {
  const result: Record<string, { path: string[]; file: string[] }> = {}
  if (!text.trim()) return result
  const pairs = text.split(';').filter(s => s.trim())
  for (const pair of pairs) {
    const colonIdx = pair.indexOf(':')
    if (colonIdx < 0) continue
    const dt = pair.substring(0, colonIdx).trim()
    const kwStr = pair.substring(colonIdx + 1).trim()
    if (!dt) continue
    const fileKws = kwStr ? kwStr.split(',').map(k => k.trim()).filter(k => k) : []
    result[dt] = { path: [], file: fileKws }
  }
  return result
}

// keyword-map dict → 紧凑格式
function serializeCompact(data: Record<string, { path: string[]; file: string[] }>): string {
  const parts: string[] = []
  // 按 docTypes 顺序输出，保持一致性
  const orderedKeys = props.docTypes.length
    ? props.docTypes.filter(dt => data[dt])
    : Object.keys(data)
  for (const dt of orderedKeys) {
    const entry = data[dt]
    if (!entry) continue
    const allKws = [...(entry.path || []), ...(entry.file || [])]
    if (allKws.length) {
      parts.push(`${dt}:${allKws.join(',')}`)
    }
  }
  return parts.join(';')
}

const compactText = computed(() => serializeCompact(props.modelValue || {}))

function onCompactTextChange(text: string) {
  const parsed = parseCompact(text)
  emit('update:modelValue', parsed)
}

function getKeywords(dt: string, field: 'path' | 'file'): string[] {
  return props.modelValue?.[dt]?.[field] || []
}

function setKeywords(dt: string, field: 'path' | 'file', val: string[]) {
  const newVal: Record<string, { path: string[]; file: string[] }> = {}
  for (const [k, v] of Object.entries(props.modelValue || {})) {
    newVal[k] = { ...v }
  }
  if (!newVal[dt]) {
    newVal[dt] = { path: [], file: [] }
  }
  newVal[dt][field] = val
  const filtered: Record<string, { path: string[]; file: string[] }> = {}
  for (const [k, v] of Object.entries(newVal)) {
    if (v.path.length || v.file.length) {
      filtered[k] = v
    }
  }
  emit('update:modelValue', filtered)
}
</script>

<style scoped>
.keyword-map-input {
  max-height: 400px;
  overflow-y: auto;
}
.mode-switch {
  margin-bottom: 10px;
}
.keyword-group {
  margin-bottom: 12px;
  padding: 8px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
.keyword-group:last-child {
  margin-bottom: 0;
}
.group-header {
  margin-bottom: 8px;
}
.group-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.field-label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  min-width: 70px;
}
.usage-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 10px;
  background: #f0f9eb;
  border-radius: 4px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #67c23a;
  line-height: 1.5;
}
.usage-tip span {
  color: #606266;
}
.usage-tip code {
  background: #e8f4e8;
  padding: 1px 4px;
  border-radius: 2px;
  font-size: 11px;
  color: #333;
}
</style>
