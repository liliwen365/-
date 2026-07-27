<template>
  <div>
    <el-card>
      <template #header>授权管理</template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="机器码（设备标识）">
          <el-input :model-value="authStore.machineId" readonly>
            <template #append>
              <el-button @click="copyMachineId">复制</el-button>
            </template>
          </el-input>
          <div style="color:#909399;font-size:12px;margin-top:4px">此码用于标识当前设备，请复制后发送给供应商以获取授权码</div>
        </el-descriptions-item>
        <el-descriptions-item label="授权状态">
          <el-tag :type="authStore.activated ? 'success' : 'danger'">
            {{ authStore.activated ? '已授权' : '未授权' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="!authStore.activated" style="margin-top: 16px">
        <el-input v-model="licenseCode" type="textarea" :rows="3" placeholder="请粘贴从供应商获取的授权码" />
        <el-button type="primary" style="margin-top: 8px" :loading="activating" @click="onActivate">
          验证并激活
        </el-button>
      </div>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header>关于</template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="版本">
          v{{ sysInfo.version || '...' }}
          <span v-if="sysInfo.build_commit && sysInfo.build_commit !== 'dev'" style="color:#909399;font-size:12px;margin-left:8px">
            ({{ sysInfo.build_commit }}, {{ sysInfo.build_time }})
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="操作系统">{{ sysInfo.platform || '...' }}</el-descriptions-item>
        <el-descriptions-item label="数据存储位置">{{ sysInfo.data_dir || '...' }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 12px; display: flex; gap: 8px">
        <el-button size="small" @click="openLogDir">打开日志目录</el-button>
        <el-button size="small" @click="copyDiagnostic">复制诊断信息</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { systemApi } from '@/api'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()
const licenseCode = ref('')
const activating = ref(false)
const sysInfo = reactive<any>({})

onMounted(async () => {
  authStore.checkStatus()
  try {
    const { data } = await systemApi.getInfo()
    Object.assign(sysInfo, data)
  } catch {
    // silent
  }
})

async function openLogDir() {
  const logDir = sysInfo.log_dir
  if (!logDir) { ElMessage.warning('未知日志目录'); return }
  try {
    const { data } = await systemApi.openFolder(logDir)
    if (!data.success) ElMessage.error(data.message || '打开失败,日志目录可能尚未生成')
  } catch {
    ElMessage.error('打开日志目录失败')
  }
}

async function copyDiagnostic() {
  try {
    const { data } = await systemApi.getDiagnostic()
    const tasks = (data.recent_tasks || []).map((t: any) =>
      `  #${t.id} ${t.plugin}/${t.feature || '-'} ${t.status} ${t.created}${t.error ? ' ⚠' + t.error : ''}`
    )
    const lines = [
      '=== 本地自动化平台 诊断信息 ===',
      `版本: v${data.version} (${data.build_commit}, ${data.build_time})`,
      `系统: ${data.platform}`,
      `数据目录: ${data.data_dir}`,
      `日志目录: ${data.log_dir}`,
      `插件(${data.plugins_count}): ${(data.plugins_loaded || []).join(', ') || '无'}`,
      (data.load_errors?.length ? `插件加载错误: ${JSON.stringify(data.load_errors)}` : ''),
      '最近任务:',
      ...tasks,
    ].filter(Boolean)
    const text = lines.join('\n')
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    ElMessage.success('诊断信息已复制,可粘贴发给开发者')
  } catch {
    ElMessage.error('获取诊断信息失败')
  }
}

function copyMachineId() {
  const text = authStore.machineId
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text)
  } else {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  ElMessage.success('机器码已复制，请发送给供应商以获取授权码')
}

async function onActivate() {
  if (!licenseCode.value.trim()) {
    ElMessage.warning('请输入授权码')
    return
  }
  activating.value = true
  try {
    const data = await authStore.activate(licenseCode.value.trim())
    if (data.success) {
      ElMessage.success('激活成功！')
    } else {
      ElMessage.error(data.message)
    }
  } catch {
    ElMessage.error('激活失败，请检查网络连接后重试。如问题持续，请联系供应商。')
  } finally {
    activating.value = false
  }
}
</script>
