<template>
  <div class="plugin-page">
    <!-- 操作指引 -->
    <el-alert v-if="!hasConfig" type="info" :closable="false" style="margin-bottom: 16px">
      <template #title>欢迎使用「{{ pluginInfo.display_name }}」</template>
      <p>请先配置任务和规则，然后点击"扫描"开始整理文件。</p>
      <p>可点击下方"加载模板"快速填充预设配置。</p>
    </el-alert>

    <!-- 模板加载 -->
    <el-dropdown v-if="pluginInfo.templates?.length" style="margin-bottom: 16px" @command="onLoadTemplate">
      <el-button>加载模板<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item v-for="t in pluginInfo.templates" :key="t.name" :command="t.name">
            {{ t.name }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>

    <!-- 参数配置区 -->
    <el-card v-for="param in pluginInfo.params" :key="param.name" style="margin-bottom: 16px">
      <template #header>
        <span>{{ param.label }}</span>
        <span v-if="param.help" style="color: #999; font-size: 12px; margin-left: 8px">{{ param.help }}</span>
      </template>
      <SchemaTable v-if="param.type === 'table'" :schema="param" v-model="formData[param.name]" />
      <div v-else>{{ param.label }}: <el-input v-model="formData[param.name]" /></div>
    </el-card>

    <!-- 操作按钮 -->
    <el-button type="primary" size="large" :loading="running" @click="onScan">
      <el-icon><Search /></el-icon> 扫描
    </el-button>
    <el-button type="success" size="large" :loading="running" :disabled="!plan.length" @click="onCopy">
      <el-icon><CopyDocument /></el-icon> 复制
    </el-button>

    <!-- 进度条 -->
    <el-progress v-if="running" :percentage="progress.percent" :format="() => progress.message" style="margin-top: 16px" />

    <!-- 结果展示 -->
    <el-card v-if="plan.length" style="margin-top: 16px">
      <template #header>执行计划 ({{ plan.length }} 条)</template>
      <el-table :data="plan" max-height="400" size="small">
        <el-table-column prop="任务ID" label="任务ID" width="120" />
        <el-table-column prop="文件分类" label="分类" width="80" />
        <el-table-column prop="查找状态" label="查找状态" width="80" />
        <el-table-column prop="复制状态" label="复制状态" width="80" />
        <el-table-column prop="源文件路径" label="源文件" show-overflow-tooltip />
        <el-table-column prop="目标文件路径" label="目标" show-overflow-tooltip />
        <el-table-column prop="错误信息" label="错误" width="150" show-overflow-tooltip />
      </el-table>
    </el-card>
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

const hasConfig = computed(() => {
  const tasks = formData.value.tasks
  return Array.isArray(tasks) && tasks.length > 0
})

onMounted(async () => {
  const { data } = await pluginApi.getInfo(pluginName.value)
  pluginInfo.value = data
  const { data: config } = await pluginApi.getConfig(pluginName.value)
  formData.value = config
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
</script>
