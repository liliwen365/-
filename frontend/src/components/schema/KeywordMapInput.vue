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
        <span>直接粘贴或编辑关键字文本，方便批量设置。</span>
      </div>
      <div class="format-help">
        <p><b>格式：</b><code>分类:路径关键词|文件关键词</code>，多个分类用分号 <code>;</code> 分隔，多个关键词用逗号 <code>,</code> 分隔</p>
        <p><b>路径关键词</b>（|前面）用于替换搜索路径中的占位符；<b>文件关键词</b>（|后面）用于匹配文件名</p>
        <p>若只写关键词不加|，则默认为<b>文件关键词</b>（兼容旧格式）</p>
        <p><b>示例：</b></p>
        <pre class="format-example">采购合同:.|.
发票:202603批次|26432000000695401411
报关单:202603批次|报关单
销售合同:.|.</pre>
      </div>
      <el-input
        :model-value="compactText"
        @update:model-value="onCompactTextChange"
        type="textarea"
        :rows="6"
        placeholder="采购合同:.|.&#10;发票:202603批次|26432000000695401411&#10;报关单:202603批次|报关单"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'
import { parseCompact, serializeCompact } from './keywordUtils'

const props = defineProps<{
  modelValue: Record<string, { path: string[]; file: string[] }>
  docTypes: string[]
}>()
const emit = defineEmits(['update:modelValue'])

const mode = ref<'visual' | 'text'>('visual')

const compactText = computed(() => serializeCompact(props.modelValue || {}, props.docTypes))

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
.format-help {
  margin-bottom: 10px;
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}
.format-help p {
  margin: 3px 0;
}
.format-help code {
  background: #f5f7fa;
  padding: 1px 4px;
  border-radius: 2px;
  font-size: 11px;
  color: #333;
}
.format-example {
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #303133;
  line-height: 1.6;
  margin: 4px 0;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: break-word;
}
</style>
