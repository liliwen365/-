<template>
  <div class="schema-table">
    <div style="margin-bottom: 8px; display: flex; justify-content: space-between">
      <span style="color: #666; font-size: 12px">共 {{ modelValue.length }} 条</span>
      <div>
        <el-button size="small" @click="onAdd">添加</el-button>
        <el-button size="small" type="danger" :disabled="!selected.length" @click="onDel">删除</el-button>
      </div>
    </div>
    <el-table :data="modelValue" @selection-change="onSelectionChange" size="small" border max-height="400">
      <el-table-column type="selection" width="40" />
      <el-table-column v-for="col in schema.columns" :key="col.name" :label="col.label" :width="col.width">
        <template #default="{ row, $index }">
          <el-select v-if="col.type === 'select'" v-model="row[col.name]" size="small" placeholder="选择">
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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ schema: any; modelValue: any[] }>()
const emit = defineEmits(['update:modelValue'])
const selected = ref<any[]>([])

function onSelectionChange(rows: any[]) {
  selected.value = rows
}

function onAdd() {
  const row: any = {}
  for (const col of props.schema.columns || []) {
    row[col.name] = col.type === 'switch' ? (col.default ?? true) : (col.default ?? '')
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
</script>
