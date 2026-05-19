<template>
  <div class="schema-table">
    <div style="margin-bottom: 8px; display: flex; justify-content: space-between">
      <span style="color: #666; font-size: 12px">共 {{ modelValue.length }} 条</span>
      <div>
        <el-button size="small" @click="onAdd">添加</el-button>
        <el-button size="small" @click="showBatchImport = true">批量导入</el-button>
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
            <span v-if="!Object.keys(row[col.name] || {}).length" style="color: #c0c4cc; font-size: 12px">点击配置</span>
          </div>
          <el-select v-else-if="col.type === 'select'" v-model="row[col.name]" size="small" placeholder="选择">
            <el-option v-for="opt in col.options" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <el-switch v-else-if="col.type === 'switch'" v-model="row[col.name]" size="small" />
          <el-input v-else-if="col.type === 'path'" v-model="row[col.name]" size="small" :placeholder="col.placeholder">
            <template #append>
              <el-button @click="browsePath(col.name, $index)">浏览</el-button>
            </template>
          </el-input>
          <el-input v-else v-model="row[col.name]" size="small" :placeholder="col.placeholder || ''" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 关键字配置对话框 -->
    <el-dialog v-model="keywordDialogVisible" title="关键字配置" width="560px" destroy-on-close>
      <KeywordMapInput
        v-model="keywordDialogValue"
        :doc-types="docTypes"
      />
      <template #footer>
        <el-button @click="keywordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveKeywordDialog">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="showBatchImport" title="批量导入任务" width="600px" destroy-on-close>
      <p style="color: #909399; font-size: 12px; margin-bottom: 8px">
        从Excel复制多行数据，粘贴到下方。格式：任务ID(Tab)目标路径，每行一个任务
      </p>
      <el-input
        v-model="batchText"
        type="textarea"
        :rows="8"
        placeholder="在此粘贴Excel数据..."
        @paste="onBatchPaste"
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
import { QuestionFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import KeywordMapInput from './KeywordMapInput.vue'

const props = defineProps<{
  schema: any
  modelValue: any[]
  /** 规则表数据，用于提取doc_type列表 */
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

// 关键字对话框
const keywordDialogVisible = ref(false)
const keywordDialogValue = ref<Record<string, { path: string[]; file: string[] }>>({})
let keywordDialogColName = ''
let keywordDialogRowIndex = -1

function openKeywordDialog(colName: string, index: number) {
  keywordDialogColName = colName
  keywordDialogRowIndex = index
  const current = props.modelValue[index][colName] || {}
  // 深拷贝确保编辑不影响原数据
  keywordDialogValue.value = JSON.parse(JSON.stringify(current))
  keywordDialogVisible.value = true
}

function saveKeywordDialog() {
  const rows = [...props.modelValue]
  rows[keywordDialogRowIndex][keywordDialogColName] = keywordDialogValue.value
  emit('update:modelValue', rows)
  keywordDialogVisible.value = false
}

// 批量导入
const showBatchImport = ref(false)
const batchText = ref('')

function onBatchPaste(e: ClipboardEvent) {
  // 延迟让textarea接收粘贴内容
  setTimeout(() => {
    // 只做格式化，不自动导入
  }, 0)
}

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
    // 按列顺序填充：第一列=task_id, 第二列=dest_root
    const textCols = (props.schema.columns || []).filter((c: any) => c.type === 'text' || c.type === 'path')
    for (let i = 0; i < Math.min(parts.length, textCols.length); i++) {
      row[textCols[i].name] = parts[i].trim()
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
</style>
