<template>
  <div class="plugin-page">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <h2>{{ pluginInfo.display_name || '文件整理' }}</h2>
      <div class="header-actions">
        <el-dropdown v-if="pluginInfo.templates?.length" @command="onLoadTemplate">
          <el-button size="small">加载模板<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="t in pluginInfo.templates" :key="t.name" :command="t.name">
                {{ t.name }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button size="small" @click="rulesDialogVisible = true">
          <el-icon><Setting /></el-icon> 规则设置
        </el-button>
        <el-button size="small" @click="historyDialogVisible = true">
          <el-icon><Clock /></el-icon> 历史
        </el-button>
      </div>
    </div>

    <!-- 首次使用引导 -->
    <el-alert v-if="!formData.rules?.length" type="info" :closable="false" style="margin-bottom: 16px">
      <template #title>欢迎使用「文件整理」</template>
      <p><b>使用步骤：</b></p>
      <ol style="margin: 4px 0; padding-left: 20px">
        <li>点击下方<b>「加载模板」</b>选择规则模板（如"出口退税资料整理"），或手动<b>「配置规则」</b></li>
        <li>在任务清单中<b>添加任务</b>，每个任务填写：任务ID、目标路径、关键字配置</li>
        <li>点击<b>「扫描」</b>查找匹配文件，确认后点击<b>「复制」</b></li>
      </ol>
      <p style="color: #909399; font-size: 12px">规则配置一次后无需重复设置，日常只需添加新任务即可。月中新增文件后，直接再点扫描即可。</p>
      <div style="margin-top: 8px">
        <el-dropdown v-if="pluginInfo.templates?.length" style="margin-right: 8px" @command="onLoadTemplate">
          <el-button size="small" type="primary">加载模板</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="t in pluginInfo.templates" :key="t.name" :command="t.name">
                {{ t.name }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button size="small" @click="rulesDialogVisible = true">手动配置规则</el-button>
      </div>
    </el-alert>

    <!-- 规则概览条 -->
    <div v-if="formData.rules?.length" class="rules-summary">
      <el-icon><InfoFilled /></el-icon>
      <span>当前规则: {{ formData.rules.length }} 条</span>
      <span v-for="r in formData.rules.filter((r: any) => r.enabled)" :key="r.doc_type" style="margin-left: 4px">
        <el-tag size="small" type="primary">{{ r.doc_type }}</el-tag>
      </span>
      <el-button link size="small" @click="rulesDialogVisible = true" style="margin-left: 8px">修改</el-button>
    </div>

    <!-- 任务清单（主区域） -->
    <el-card style="margin-top: 16px">
      <template #header>
        <span>任务清单</span>
        <span style="color: #999; font-size: 12px; margin-left: 8px">
          点击「添加」新增任务，或「批量导入」从Excel粘贴。点击「关键字配置」列设置各分类的关键词
        </span>
      </template>
      <SchemaTable
        v-if="tasksParam"
        :schema="tasksParam"
        v-model="formData.tasks"
        :rules-data="formData.rules"
      />
    </el-card>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <el-button
        type="primary"
        size="large"
        :loading="running"
        :disabled="!formData.tasks?.length || !formData.rules?.length"
        @click="onScan"
      >
        <el-icon><Search /></el-icon> 扫描
      </el-button>
      <el-button
        type="success"
        size="large"
        :loading="running"
        :disabled="!foundCount"
        @click="onCopy"
      >
        <el-icon><CopyDocument /></el-icon> 复制 ({{ foundCount }} 个文件)
      </el-button>
    </div>

    <!-- 进度条 -->
    <el-progress
      v-if="running"
      :percentage="progress.percent"
      :format="() => progress.message"
      style="margin-top: 16px"
      :stroke-width="18"
      striped
      striped-flow
    />

    <!-- 扫描/复制结果 -->
    <el-card v-if="plan.length" style="margin-top: 16px">
      <template #header>
        <span>{{ copyDone ? '复制结果' : '扫描结果' }}</span>
        <el-tag type="success" style="margin-left: 8px">找到 {{ foundCount }} 个文件</el-tag>
        <el-tag v-if="failCount" type="danger" style="margin-left: 4px">{{ failCount }} 项查找失败</el-tag>
        <el-tag v-if="copyDone && copiedCount" type="success" style="margin-left: 4px">已复制 {{ copiedCount }}</el-tag>
        <el-tag v-if="copyDone && failedCount" type="danger" style="margin-left: 4px">失败 {{ failedCount }}</el-tag>
      </template>
      <el-table :data="plan" max-height="400" size="small" border>
        <el-table-column prop="task_id" label="任务ID" width="120" />
        <el-table-column prop="doc_type" label="分类" width="80" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag
              v-if="row.copy_status"
              :type="row.copy_status === '已复制' ? 'success' : row.copy_status === '用户跳过' ? 'info' : 'danger'"
              size="small"
            >{{ row.copy_status }}</el-tag>
            <el-tag v-else :type="row.find_status === '已找到' ? 'success' : 'danger'" size="small">
              {{ row.find_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="file_mtime" label="修改时间" width="140" />
        <el-table-column prop="source_path" label="源文件" show-overflow-tooltip />
        <el-table-column prop="dest_path" label="目标路径" show-overflow-tooltip />
        <el-table-column prop="error_msg" label="错误" width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="80" v-if="copyDone">
          <template #default="{ row }">
            <el-button
              v-if="row.copy_status === '已复制' && row.dest_path"
              link type="primary" size="small"
              @click="openFolder(row.dest_path)"
            >打开</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 规则设置对话框 -->
    <el-dialog v-model="rulesDialogVisible" title="规则设置" width="900px" destroy-on-close>
      <el-alert type="info" :closable="false" style="margin-bottom: 12px">
        <template #title>规则说明</template>
        <p>规则定义了各类文件的搜索方式。配置一次后通常不需要修改，日常只需添加任务。</p>
        <p><b>文件名匹配规则</b>：使用通配符模式匹配文件名。</p>
        <ul style="margin: 4px 0; padding-left: 20px">
          <li><code>*</code> — 匹配任意字符，如 <code>*发票*</code> 匹配所有文件名含"发票"的文件</li>
          <li><code>{文件关键词}</code> — 替换为你输入的文件关键词</li>
          <li><code>{文件分类}</code> — 替换为当前规则分类名（如"发票"、"报关单"）</li>
          <li>示例：<code>*{文件关键词}*发票*.*</code>，输入关键词"ABC001"后匹配 <code>*ABC001*发票*.*</code></li>
        </ul>
        <p><b>搜索路径</b>：使用 <code>{路径关键词}</code> 占位符，扫描时会替换为任务中配置的路径关键词。</p>
      </el-alert>
      <SchemaTable
        v-if="rulesParam"
        :schema="rulesParam"
        v-model="formData.rules"
      />
      <template #footer>
        <el-button @click="rulesDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>

    <!-- 历史记录对话框 -->
    <el-dialog v-model="historyDialogVisible" title="执行历史" width="700px" destroy-on-close>
      <el-table :data="history" size="small" border v-loading="historyLoading">
        <el-table-column prop="id" label="#" width="60" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="结果" show-overflow-tooltip />
        <el-table-column prop="created_at" label="执行时间" width="170" />
      </el-table>
      <el-empty v-if="!history.length && !historyLoading" description="暂无执行记录" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { pluginApi, systemApi } from '@/api'
import { ElMessage } from 'element-plus'
import SchemaTable from '@/components/schema/SchemaTable.vue'

const route = useRoute()
const pluginName = computed(() => route.path.replace('/plugin/', ''))

const pluginInfo = ref<any>({})
const formData = ref<any>({ tasks: [], rules: [] })
const plan = ref<any[]>([])
const running = ref(false)
const progress = ref({ percent: 0, message: '' })
const copyDone = ref(false)

// 对话框
const rulesDialogVisible = ref(false)
const historyDialogVisible = ref(false)
const history = ref<any[]>([])
const historyLoading = ref(false)

// schema
const tasksParam = computed(() => pluginInfo.value.params?.find((p: any) => p.name === 'tasks'))
const rulesParam = computed(() => pluginInfo.value.params?.find((p: any) => p.name === 'rules'))

// 统计
const foundCount = computed(() => plan.value.filter(r => r.find_status === '已找到').length)
const failCount = computed(() => plan.value.filter(r => r.find_status === '查找失败').length)
const copiedCount = computed(() => plan.value.filter(r => r.copy_status === '已复制').length)
const failedCount = computed(() => plan.value.filter(r => r.copy_status === '复制失败').length)

function formatSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

// 自动保存
let saveTimer: ReturnType<typeof setTimeout> | null = null
watch(formData, () => {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => saveConfig(), 1000)
}, { deep: true })

async function saveConfig() {
  try {
    await pluginApi.saveConfig(pluginName.value, formData.value)
  } catch {
    // 静默失败，不干扰用户
  }
}

onMounted(async () => {
  const { data } = await pluginApi.getInfo(pluginName.value)
  pluginInfo.value = data
  const { data: config } = await pluginApi.getConfig(pluginName.value)
  formData.value = config

  // 首次无规则自动弹出模板选择
  if (!formData.value.rules?.length && pluginInfo.value.templates?.length) {
    rulesDialogVisible.value = true
  }
})

async function onLoadTemplate(name: string) {
  try {
    const { data } = await pluginApi.loadTemplate(pluginName.value, name)
    const rules = Array.isArray(data) ? data : data.rules || []
    if (rules.length) {
      formData.value.rules = rules
      ElMessage.success(`已加载模板「${name}」`)
      saveConfig()
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

async function onScan() {
  if (!formData.value.tasks?.length) {
    ElMessage.warning('请先添加任务')
    return
  }
  if (!formData.value.rules?.length) {
    ElMessage.warning('请先配置规则')
    return
  }
  running.value = true
  progress.value = { percent: 0, message: '扫描中...' }
  plan.value = []
  copyDone.value = false
  try {
    const { data } = await pluginApi.execute(pluginName.value, { ...formData.value, action: 'scan' })
    if (data.status === 'success') {
      plan.value = data.data?.plan || []
      if (data.data?.tasks) {
        formData.value.tasks = data.data.tasks
      }
      ElMessage.success(data.summary)
    } else {
      ElMessage.error(data.summary)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '扫描失败')
  } finally {
    running.value = false
  }
}

async function onCopy() {
  running.value = true
  progress.value = { percent: 0, message: '复制中...' }
  try {
    const { data } = await pluginApi.execute(pluginName.value, { ...formData.value, action: 'copy', plan: plan.value })
    if (data.status === 'success') {
      plan.value = data.data?.plan || plan.value
      copyDone.value = true
      ElMessage.success(data.summary)
    } else {
      ElMessage.error(data.summary)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '复制失败')
  } finally {
    running.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const { data } = await pluginApi.getHistory(pluginName.value)
    history.value = data.history || []
  } catch {
    history.value = []
  } finally {
    historyLoading.value = false
  }
}

// 打开历史时加载数据
watch(historyDialogVisible, (v) => {
  if (v) loadHistory()
})

async function openFolder(filePath: string) {
  // 打开文件所在目录
  const dir = filePath.substring(0, filePath.lastIndexOf('/'))
  try {
    await systemApi.openFolder(dir)
  } catch {
    ElMessage.error('无法打开文件夹')
  }
}
</script>

<style scoped>
.plugin-page {
  max-width: 1100px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.rules-summary {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
}
.action-bar {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}
</style>
