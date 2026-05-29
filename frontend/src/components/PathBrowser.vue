<template>
  <el-dialog v-model="visible" :title="title" width="560px" destroy-on-close @open="loadPath(currentPath)">
    <div class="path-browser">
      <div class="path-bar">
        <el-input v-model="currentPath" size="small" placeholder="输入路径后回车" @keyup.enter="loadPath(currentPath)">
          <template #prepend>路径</template>
          <template #append>
            <el-button @click="loadPath(currentPath)">前往</el-button>
          </template>
        </el-input>
      </div>
      <div v-if="parentPath" class="nav-item" @click="loadPath(parentPath)">
        <el-icon><Back /></el-icon>
        <span>..</span>
      </div>
      <div class="dir-list">
        <div v-if="loading" style="text-align: center; padding: 20px; color: #909399">加载中...</div>
        <div v-else-if="!entries.length" style="text-align: center; padding: 20px; color: #909399">
          {{ currentPath ? '该目录为空或无法访问' : '请输入路径' }}
        </div>
        <div
          v-for="entry in entries"
          :key="entry.path"
          class="dir-item"
          :title="entry.path"
          @click="loadPath(entry.path)"
        >
          <el-icon><Folder /></el-icon>
          <span class="dir-name">{{ entry.name }}</span>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="confirm">选择此目录</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Back, Folder } from '@element-plus/icons-vue'
import api from '../api'

const props = withDefaults(defineProps<{
  title?: string
}>(), {
  title: '选择目录',
})

const visible = ref(false)
const currentPath = ref('')
const parentPath = ref<string | null>(null)
const entries = ref<{ name: string; path: string; is_dir: boolean }[]>([])
const loading = ref(false)

let resolveFn: ((path: string) => void) | null = null

function open(initialPath: string): Promise<string> {
  currentPath.value = initialPath || ''
  visible.value = true
  return new Promise(resolve => { resolveFn = resolve })
}

async function loadPath(path: string) {
  if (!path) return
  loading.value = true
  currentPath.value = path
  try {
    const res = await api.post('/api/system/browse', { path, type: 'directory' })
    parentPath.value = res.data.parent && res.data.parent !== res.data.current ? res.data.parent : null
    entries.value = res.data.entries || []
  } catch {
    entries.value = []
    parentPath.value = null
  } finally {
    loading.value = false
  }
}

function confirm() {
  visible.value = false
  resolveFn?.(currentPath.value)
  resolveFn = null
}

defineExpose({ open })
</script>

<style scoped>
.path-browser { border: 1px solid #dcdfe6; border-radius: 4px; overflow: hidden; }
.path-bar { padding: 8px; border-bottom: 1px solid #ebeef5; background: #f5f7fa; }
.dir-list { max-height: 320px; overflow-y: auto; }
.nav-item, .dir-item {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; cursor: pointer; font-size: 13px;
}
.nav-item:hover, .dir-item:hover { background: #ecf5ff; }
.dir-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
