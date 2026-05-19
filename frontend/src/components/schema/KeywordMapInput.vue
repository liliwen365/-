<template>
  <div class="keyword-map-input">
    <!-- 使用提示 -->
    <div class="usage-tip">
      <el-icon><InfoFilled /></el-icon>
      <span>为每个文件分类设置关键词：输入文字后按回车添加标签。<b>路径关键词</b>用于替换搜索路径中的占位符，<b>文件关键词</b>用于匹配文件名。输入<b>.</b>表示匹配该路径下所有文件。</span>
    </div>

    <!-- 无分类时提示 -->
    <el-empty v-if="!docTypes.length" description="请先在规则库中添加文件分类" :image-size="60" />

    <!-- 按文件分类分组的关键字输入 -->
    <div v-for="dt in docTypes" :key="dt" class="keyword-group">
      <div class="group-header">
        <el-tag size="small" type="primary">{{ dt }}</el-tag>
      </div>
      <div class="group-fields">
        <div class="field-row">
          <span class="field-label">路径关键词</span>
          <el-select
            v-model="innerValue[dt].path"
            multiple
            filterable
            allow-create
            default-first-option
            :reserve-keyword="false"
            placeholder="输入后回车添加"
            size="small"
            style="flex: 1"
          />
        </div>
        <div class="field-row">
          <span class="field-label">文件关键词</span>
          <el-select
            v-model="innerValue[dt].file"
            multiple
            filterable
            allow-create
            default-first-option
            :reserve-keyword="false"
            placeholder="输入后回车，.匹配所有文件"
            size="small"
            style="flex: 1"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: Record<string, { path: string[]; file: string[] }>
  docTypes: string[]
}>()
const emit = defineEmits(['update:modelValue'])

// 确保每个docType都有条目
const innerValue = computed(() => {
  const val: Record<string, { path: string[]; file: string[] }> = {}
  for (const dt of props.docTypes) {
    val[dt] = props.modelValue?.[dt] || { path: [], file: [] }
  }
  return val
})

// 深度监听变化并emit
watch(
  () => innerValue.value,
  (newVal) => {
    // 只emit有值的分类，避免空数据污染
    const filtered: Record<string, { path: string[]; file: string[] }> = {}
    for (const [k, v] of Object.entries(newVal)) {
      if (v.path.length || v.file.length) {
        filtered[k] = v
      }
    }
    emit('update:modelValue', filtered)
  },
  { deep: true }
)
</script>

<style scoped>
.keyword-map-input {
  max-height: 400px;
  overflow-y: auto;
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
</style>
