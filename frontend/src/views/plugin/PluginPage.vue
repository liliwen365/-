<template>
  <div class="plugin-page">
    <!-- 步骤引导 -->
    <el-steps :active="currentStep" finish-status="success" simple style="margin-bottom: 20px">
      <el-step title="配置规则" />
      <el-step title="添加任务" />
      <el-step title="扫描预览" />
      <el-step title="执行复制" />
    </el-steps>

    <!-- 步骤1: 规则配置 -->
    <div v-show="currentStep === 0">
      <el-alert v-if="!formData.rules?.length" type="info" :closable="false" style="margin-bottom: 16px">
        <template #title>欢迎使用「{{ pluginInfo.display_name }}」</template>
        <p>先加载规则模板或手动添加规则，定义各类文件的搜索路径和匹配模式。</p>
      </el-alert>

      <div style="margin-bottom: 12px; display: flex; gap: 8px">
        <el-dropdown v-if="pluginInfo.templates?.length" @command="onLoadTemplate">
          <el-button>加载模板<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="t in pluginInfo.templates" :key="t.name" :command="t.name">
                {{ t.name }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <el-card>
        <template #header>
          <span>文件规则库</span>
          <span style="color: #999; font-size: 12px; margin-left: 8px">定义各类文件的搜索路径、文件名模式和目标子文件夹</span>
        </template>
        <SchemaTable
          v-if="rulesParam"
          :schema="rulesParam"
          v-model="formData.rules"
        />
      </el-card>

      <div style="margin-top: 16px; text-align: right">
        <el-button type="primary" :disabled="!formData.rules?.length" @click="currentStep = 1">
          下一步：添加任务
        </el-button>
      </div>
    </div>

    <!-- 步骤2: 任务添加 -->
    <div v-show="currentStep === 1">
      <el-card>
        <template #header>
          <span>任务清单</span>
          <span style="color: #999; font-size: 12px; margin-left: 8px">每个任务对应一个报关单/合同的文件整理</span>
        </template>
        <SchemaTable
          v-if="tasksParam"
          :schema="tasksParam"
          v-model="formData.tasks"
          :rules-data="formData.rules"
        />
      </el-card>

      <div style="margin-top: 16px; display: flex; justify-content: space-between">
        <el-button @click="currentStep = 0">上一步</el-button>
        <el-button type="primary" :disabled="!formData.tasks?.length" @click="currentStep = 2">
          下一步：扫描预览
        </el-button>
      </div>
    </div>

    <!-- 步骤3: 扫描预览 -->
    <div v-show="currentStep === 2">
      <el-card>
        <template #header>扫描文件</template>
        <p style="color: #909399; margin-bottom: 12px">
          点击"开始扫描"查找匹配的文件，扫描完成后可预览结果并标记跳过。
        </p>
        <el-button type="primary" size="large" :loading="running" @click="onScan">
          <el-icon><Search /></el-icon> 开始扫描
        </el-button>
      </el-card>

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

      <!-- 扫描结果 -->
      <el-card v-if="plan.length" style="margin-top: 16px">
        <template #header>
          <span>扫描结果</span>
          <el-tag type="success" style="margin-left: 8px">找到 {{ foundCount }} 个文件</el-tag>
          <el-tag v-if="failCount" type="danger" style="margin-left: 4px">{{ failCount }} 项查找失败</el-tag>
        </template>
        <el-table :data="plan" max-height="400" size="small" border>
          <el-table-column prop="task_id" label="任务ID" width="120" />
          <el-table-column prop="doc_type" label="分类" width="80" />
          <el-table-column label="查找状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.find_status === '已找到' ? 'success' : 'danger'" size="small">
                {{ row.find_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="文件大小" width="100">
            <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
          </el-table-column>
          <el-table-column prop="file_mtime" label="修改时间" width="140" />
          <el-table-column prop="source_path" label="源文件" show-overflow-tooltip />
          <el-table-column prop="dest_path" label="目标路径" show-overflow-tooltip />
          <el-table-column prop="error_msg" label="错误" width="150" show-overflow-tooltip />
        </el-table>
      </el-card>

      <div style="margin-top: 16px; display: flex; justify-content: space-between">
        <el-button @click="currentStep = 1">上一步</el-button>
        <el-button type="success" :disabled="!foundCount || running" @click="currentStep = 3">
          下一步：执行复制
        </el-button>
      </div>
    </div>

    <!-- 步骤4: 执行复制 -->
    <div v-show="currentStep === 3">
      <el-card>
        <template #header>执行复制</template>
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="待复制文件">{{ foundCount }} 个</el-descriptions-item>
          <el-descriptions-item label="查找失败">{{ failCount }} 项</el-descriptions-item>
        </el-descriptions>
        <el-button type="success" size="large" :loading="running" @click="onCopy">
          <el-icon><CopyDocument /></el-icon> 确认复制
        </el-button>
      </el-card>

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

      <!-- 复制结果 -->
      <el-card v-if="copyDone" style="margin-top: 16px">
        <template #header>
          <span>复制结果</span>
          <el-tag type="success" style="margin-left: 8px">成功 {{ copiedCount }}</el-tag>
          <el-tag v-if="failedCount" type="danger" style="margin-left: 4px">失败 {{ failedCount }}</el-tag>
          <el-tag v-if="skippedCount" type="info" style="margin-left: 4px">跳过 {{ skippedCount }}</el-tag>
        </template>
        <el-table :data="plan" max-height="400" size="small" border>
          <el-table-column prop="task_id" label="任务ID" width="120" />
          <el-table-column prop="doc_type" label="分类" width="80" />
          <el-table-column label="复制状态" width="90">
            <template #default="{ row }">
              <el-tag
                :type="row.copy_status === '已复制' ? 'success' : row.copy_status === '用户跳过' ? 'info' : 'danger'"
                size="small"
              >
                {{ row.copy_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source_path" label="源文件" show-overflow-tooltip />
          <el-table-column prop="dest_path" label="目标路径" show-overflow-tooltip />
          <el-table-column prop="error_msg" label="错误" width="150" show-overflow-tooltip />
        </el-table>
      </el-card>

      <div style="margin-top: 16px">
        <el-button @click="currentStep = 2">上一步</el-button>
        <el-button type="primary" @click="resetAll">重新开始</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { pluginApi } from '@/api'
import { ElMessage } from 'element-plus'
import SchemaTable from '@/components/schema/SchemaTable.vue'

const route = useRoute()
const pluginName = computed(() => route.path.replace('/plugin/', ''))

const pluginInfo = ref<any>({})
const formData = ref<any>({})
const plan = ref<any[]>([])
const running = ref(false)
const progress = ref({ percent: 0, message: '' })
const currentStep = ref(0)
const copyDone = ref(false)

// 从pluginInfo中提取tasks和rules的schema
const tasksParam = computed(() => pluginInfo.value.params?.find((p: any) => p.name === 'tasks'))
const rulesParam = computed(() => pluginInfo.value.params?.find((p: any) => p.name === 'rules'))

const foundCount = computed(() => plan.value.filter(r => r.find_status === '已找到').length)
const failCount = computed(() => plan.value.filter(r => r.find_status === '查找失败').length)
const copiedCount = computed(() => plan.value.filter(r => r.copy_status === '已复制').length)
const failedCount = computed(() => plan.value.filter(r => r.copy_status === '复制失败').length)
const skippedCount = computed(() => plan.value.filter(r => r.copy_status === '用户跳过').length)

function formatSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

onMounted(async () => {
  const { data } = await pluginApi.getInfo(pluginName.value)
  pluginInfo.value = data
  const { data: config } = await pluginApi.getConfig(pluginName.value)
  formData.value = config

  // 如果已有配置，根据情况跳到合适步骤
  if (formData.value.rules?.length && formData.value.tasks?.length) {
    currentStep.value = 2
  } else if (formData.value.rules?.length) {
    currentStep.value = 1
  }
})

async function onLoadTemplate(name: string) {
  try {
    const { data } = await pluginApi.loadTemplate(pluginName.value, name)
    const rules = Array.isArray(data) ? data : data.rules || []
    if (rules.length) {
      formData.value.rules = rules
      ElMessage.success(`已加载模板「${name}」`)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

async function onScan() {
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

function resetAll() {
  currentStep.value = 0
  plan.value = []
  copyDone.value = false
}
</script>

<style scoped>
.plugin-page {
  max-width: 1100px;
}
</style>
