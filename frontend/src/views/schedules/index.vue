<template>
  <div class="schedules-page">
    <div class="page-header">
      <h2>定时调度</h2>
      <el-button type="primary" size="small" @click="showCreate = true">
        <el-icon><Plus /></el-icon> 新建调度
      </el-button>
    </div>

    <el-alert v-if="!schedules.length" type="info" :closable="false" style="margin-bottom: 16px">
      <template #title>暂无定时调度</template>
      <p>创建定时调度后，系统将按照设定的时间自动执行插件任务。</p>
    </el-alert>

    <el-table :data="schedules" size="small" border v-loading="loading">
      <el-table-column prop="id" label="#" width="60" />
      <el-table-column prop="plugin_name" label="插件" width="120" />
      <el-table-column prop="feature_id" label="功能" width="120" />
      <el-table-column label="调度规则" width="160">
        <template #default="{ row }">
          <code style="background: #f5f7fa; padding: 2px 6px; border-radius: 2px; font-size: 12px">{{ row.cron_expr }}</code>
        </template>
      </el-table-column>
      <el-table-column label="下次执行" width="180">
        <template #default="{ row }">{{ row.next_run || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="toggleSchedule(row)">
            {{ row.enabled ? '禁用' : '启用' }}
          </el-button>
          <el-button link size="small" type="danger" @click="deleteSchedule(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建调度对话框 -->
    <el-dialog v-model="showCreate" title="新建定时调度" width="500px" destroy-on-close>
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="插件" required>
          <el-select v-model="form.plugin_name" placeholder="选择插件" style="width: 100%">
            <el-option v-for="p in plugins" :key="p.name" :label="p.display_name" :value="p.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="功能ID">
          <el-input v-model="form.feature_id" placeholder="如 scan_and_copy（留空用默认）" />
        </el-form-item>
        <el-form-item label="Cron表达式" required>
          <el-input v-model="form.cron_expr" placeholder="分 时 日 月 周，如 0 9 1 * *" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px">
            格式：分 时 日 月 周。示例：<code>0 9 1 * *</code> = 每月1号9点
          </div>
        </el-form-item>
        <el-form-item label="参数(JSON)">
          <el-input v-model="form.params_text" type="textarea" :rows="3" placeholder='{"action": "scan"}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createSchedule">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const schedules = ref<any[]>([])
const plugins = ref<any[]>([])
const loading = ref(false)
const showCreate = ref(false)

const form = ref({
  plugin_name: '',
  feature_id: '',
  cron_expr: '',
  params_text: '{}',
})

onMounted(async () => {
  await loadSchedules()
  await loadPlugins()
})

async function loadSchedules() {
  loading.value = true
  try {
    const { data } = await api.get('/api/schedules')
    schedules.value = data.schedules || []
  } catch {
    schedules.value = []
  } finally {
    loading.value = false
  }
}

async function loadPlugins() {
  try {
    const { data } = await api.get('/api/plugins/installed')
    plugins.value = data.plugins || []
  } catch {
    plugins.value = []
  }
}

async function createSchedule() {
  if (!form.value.plugin_name || !form.value.cron_expr) {
    ElMessage.warning('请填写插件和Cron表达式')
    return
  }
  try {
    let params = {}
    if (form.value.params_text.trim()) {
      params = JSON.parse(form.value.params_text)
    }
    await api.post('/api/schedules', {
      plugin_name: form.value.plugin_name,
      feature_id: form.value.feature_id,
      cron_expr: form.value.cron_expr,
      params,
    })
    ElMessage.success('调度创建成功')
    showCreate.value = false
    await loadSchedules()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

async function toggleSchedule(row: any) {
  try {
    await api.put(`/api/schedules/${row.id}/toggle`)
    await loadSchedules()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function deleteSchedule(id: number) {
  try {
    await api.delete(`/api/schedules/${id}`)
    ElMessage.success('已删除')
    await loadSchedules()
  } catch {
    ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.schedules-page {
  max-width: 900px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
}
</style>
