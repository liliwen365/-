<template>
  <div class="schema-table">
    <div style="margin-bottom: 8px; display: flex; justify-content: space-between">
      <span style="color: #666; font-size: 12px">共 {{ modelValue.length }} 条</span>
      <div>
        <el-button size="small" @click="onAdd">添加</el-button>
        <el-button size="small" @click="showBatchImport = true">批量导入</el-button>
        <el-button v-if="kwColName" size="small" type="warning" :disabled="!selected.length" @click="openBulkKeywordDialog">
          批量设置关键词 ({{ selected.length }})
        </el-button>
        <el-button size="small" type="danger" :disabled="!selected.length" @click="onDel">删除</el-button>
      </div>
    </div>
    <el-table :data="modelValue" @selection-change="onSelectionChange" size="small" border max-height="400">
      <el-table-column type="selection" width="40" />
      <el-table-column v-for="col in schema.columns" :key="col.name" :width="col.width">
        <template #header>
          <span>{{ col.label }}</span>
          <el-tooltip v-if="col.help" :content="col.help" placement="top">
            <el-icon style="margin-left: 4px; color: #909399; cursor: help"><QuestionFilled /></el-icon>
          </el-tooltip>
        </template>
        <template #default="{ row, $index }">
          <!-- keyword-map: 点击弹对话框 -->
          <div v-if="col.type === 'keyword-map'" class="keyword-map-cell" @click="openKeywordDialog(col.name, $index)">
            <el-tag v-for="dt in Object.keys(row[col.name] || {}).slice(0, 3)" :key="dt" size="small" style="margin-right: 2px">
              {{ dt }}({{ keywordCount(row[col.name], dt) }})
            </el-tag>
            <span v-if="Object.keys(row[col.name] || {}).length > 3" style="color: #909399; font-size: 12px">
              +{{ Object.keys(row[col.name] || {}).length - 3 }}
            </span>
            <span v-if="!Object.keys(row[col.name] || {}).length" style="color: #c0c4cc; font-size: 12px">点击设置关键词</span>
          </div>
          <el-select v-else-if="col.type === 'select'" v-model="row[col.name]" size="small" :placeholder="'请选择' + col.label">
            <el-option v-for="opt in col.options" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <el-switch v-else-if="col.type === 'switch'" v-model="row[col.name]" size="small" />
          <el-input v-else-if="col.type === 'path'" v-model="row[col.name]" size="small" :placeholder="col.placeholder">
            <template #append>
              <el-button @click="browsePath(col.name, $index)">浏览</el-button>
            </template>
          </el-input>
          <el-input v-else v-model="row[col.name]" size="small" :placeholder="col.placeholder || '请输入' + col.label" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 单行关键字配置对话框 -->
    <el-dialog v-model="keywordDialogVisible" title="搜索关键词设置" width="560px" destroy-on-close>
      <KeywordMapInput
        v-model="keywordDialogValue"
        :doc-types="docTypes"
      />
      <template #footer>
        <el-button @click="keywordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveKeywordDialog">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量设置关键字对话框（选中多行后） -->
    <el-dialog v-model="bulkKeywordVisible" title="批量设置关键词" width="560px" destroy-on-close>
      <div class="usage-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>配置的关键词将<b>覆盖</b>所有选中行的关键词设置。可在「文本模式」中直接粘贴，如：<code>采购合同:.;销售合同:.;发票:26432000000695401411</code></span>
      </div>
      <KeywordMapInput
        v-model="bulkKeywordValue"
        :doc-types="docTypes"
      />
      <template #footer>
        <el-button @click="bulkKeywordVisible = false">取消</el-button>
        <el-button type="primary" @click="saveBulkKeyword">应用到 {{ selected.length }} 行</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="showBatchImport" title="批量导入任务" width="650px" destroy-on-close>
      <div class="import-help">
        <p><b>使用方法：</b>在Excel中选中多行数据，复制后粘贴到下方输入框。</p>
        <p><b>格式要求：</b>每行一个任务，列之间用Tab分隔。</p>
        <ul style="margin: 4px 0; padding-left: 20px">
          <li>第1列=任务ID，第2列=目标存放路径</li>
          <li>第3列（可选）=关键字配置，格式：<code>分类:关键词;分类:关键词</code></li>
        </ul>
        <p><b>示例（2列，无关键字）：</b></p>
        <pre class="import-example">CG-MLG-202603090011	D:\出口退税\202603批次\出口退税资料
CG-DX-202602100009	D:\出口退税\202603批次\出口退税资料</pre>
        <p><b>示例（3列，含关键字）：</b></p>
        <pre class="import-example">CG-MLG-202603090011	D:\出口退税\202603批次\出口退税资料	采购合同:.;销售合同:.;发票:26432000000695401411;报关单:报关单
CG-DX-202602100009	D:\出口退税\202603批次\出口退税资料	采购合同:.;销售合同:.;发票:26432000000695401412;报关单:报关单</pre>
        <p style="color: #909399; font-size: 12px">提示：第3列关键字格式与Excel中一致，多个分类用分号分隔，分类名和关键词用冒号分隔。多个关键词用逗号分隔。输入 . 匹配所有文件。</p>
      </div>
      <el-input
        v-model="batchText"
        type="textarea"
        :rows="8"
        placeholder="从Excel复制后在此粘贴，每行一个任务..."
      />
      <template #footer>
        <el-button @click="showBatchImport = false">取消</el-button>
        <el-button type="primary" :disabled="!batchText.trim()" @click="doBatchImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { QuestionFilled, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import KeywordMapInput from './KeywordMapInput.vue'

const props = defineProps<{
  schema: any
  modelValue: any[]
  rulesData?: any[]
}>()
const emit = defineEmits(['update:modelValue'])
const selected = ref<any[]>([])

// 从规则表提取文件分类列表
const docTypes = computed(() => {
  if (!props.rulesData?.length) return []
  const types = new Set<string>()
  for (const r of props.rulesData) {
    if (r.doc_type) types.add(r.doc_type)
  }
  return Array.from(types)
})

// 找到 keyword-map 类型的列名
const kwColName = computed(() => {
  for (const col of props.schema.columns || []) {
    if (col.type === 'keyword-map') return col.name
  }
  return ''
})

// 紧凑格式 → keyword-map dict
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

function keywordCount(keywords: any, dt: string): number {
  if (!keywords || !keywords[dt]) return 0
  return (keywords[dt].path?.length || 0) + (keywords[dt].file?.length || 0)
}

function onSelectionChange(rows: any[]) {
  selected.value = rows
}

function onAdd() {
  const row: any = {}
  for (const col of props.schema.columns || []) {
    if (col.type === 'switch') {
      row[col.name] = col.default ?? true
    } else if (col.type === 'keyword-map') {
      row[col.name] = {}
    } else {
      row[col.name] = col.default ?? ''
    }
  }
  emit('update:modelValue', [...props.modelValue, row])
}

function onDel() {
  const set = new Set(selected.value)
  emit('update:modelValue', props.modelValue.filter((r: any) => !set.has(r)))
}

function browsePath(colName: string, index: number) {
  const input = document.createElement('input')
  input.type = 'file'
  input.webkitdirectory = true
  input.onchange = () => {
    if (input.files?.length) {
      const path = input.files[0].webkitRelativePath.split('/')[0]
      const rows = [...props.modelValue]
      rows[index][colName] = path
      emit('update:modelValue', rows)
    }
  }
  input.click()
}

// 单行关键字对话框
const keywordDialogVisible = ref(false)
const keywordDialogValue = ref<Record<string, { path: string[]; file: string[] }>>({})
let keywordDialogColName = ''
let keywordDialogRowIndex = -1

function openKeywordDialog(colName: string, index: number) {
  keywordDialogColName = colName
  keywordDialogRowIndex = index
  const current = props.modelValue[index][colName] || {}
  keywordDialogValue.value = JSON.parse(JSON.stringify(current))
  keywordDialogVisible.value = true
}

function saveKeywordDialog() {
  const rows = [...props.modelValue]
  rows[keywordDialogRowIndex][keywordDialogColName] = keywordDialogValue.value
  emit('update:modelValue', rows)
  keywordDialogVisible.value = false
}

// 批量设置关键字对话框
const bulkKeywordVisible = ref(false)
const bulkKeywordValue = ref<Record<string, { path: string[]; file: string[] }>>({})

function openBulkKeywordDialog() {
  if (!selected.value.length || !kwColName.value) return
  // 尝试取第一行的关键字作为初始值（方便复用已有配置）
  const firstRow = selected.value[0]
  const current = firstRow[kwColName.value] || {}
  bulkKeywordValue.value = JSON.parse(JSON.stringify(current))
  bulkKeywordVisible.value = true
}

function saveBulkKeyword() {
  if (!kwColName.value) return
  const rows = [...props.modelValue]
  const selectedSet = new Set(selected.value)
  const kwVal = JSON.parse(JSON.stringify(bulkKeywordValue.value))
  let count = 0
  for (let i = 0; i < rows.length; i++) {
    if (selectedSet.has(rows[i])) {
      rows[i][kwColName.value] = JSON.parse(JSON.stringify(kwVal))
      count++
    }
  }
  emit('update:modelValue', rows)
  bulkKeywordVisible.value = false
  ElMessage.success(`已为 ${count} 行设置关键词`)
}

// 批量导入
const showBatchImport = ref(false)
const batchText = ref('')

function doBatchImport() {
  const lines = batchText.value.trim().split('\n').filter(l => l.trim())
  const newRows: any[] = []
  for (const line of lines) {
    const parts = line.split('\t')
    const row: any = {}
    for (const col of props.schema.columns || []) {
      if (col.type === 'switch') {
        row[col.name] = col.default ?? true
      } else if (col.type === 'keyword-map') {
        row[col.name] = {}
      } else {
        row[col.name] = ''
      }
    }
    // 填充文本/路径列
    const textCols = (props.schema.columns || []).filter((c: any) => c.type === 'text' || c.type === 'path')
    for (let i = 0; i < Math.min(parts.length, textCols.length); i++) {
      row[textCols[i].name] = parts[i].trim()
    }
    // 如果有第3列且存在keyword-map列，解析紧凑格式
    if (parts.length > textCols.length && kwColName.value) {
      const kwText = parts.slice(textCols.length).join('\t').trim()
      if (kwText) {
        row[kwColName.value] = parseCompact(kwText)
      }
    }
    newRows.push(row)
  }
  if (newRows.length) {
    emit('update:modelValue', [...props.modelValue, ...newRows])
    ElMessage.success(`已导入 ${newRows.length} 条任务`)
  }
  showBatchImport.value = false
  batchText.value = ''
}
</script>

<style scoped>
.keyword-map-cell {
  cursor: pointer;
  min-height: 24px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
}
.keyword-map-cell:hover {
  background: #f5f7fa;
  border-radius: 2px;
}
.usage-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 10px;
  background: #fdf6ec;
  border-radius: 4px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #e6a23c;
  line-height: 1.5;
}
.usage-tip span {
  color: #606266;
}
.usage-tip code {
  background: #faecd8;
  padding: 1px 4px;
  border-radius: 2px;
  font-size: 11px;
  color: #333;
}
.import-help p {
  margin: 4px 0;
  font-size: 13px;
  color: #606266;
}
.import-example {
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #303133;
  line-height: 1.6;
  margin: 4px 0;
}
</style>
