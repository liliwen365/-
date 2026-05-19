<template>
  <div>
    <el-card>
      <template #header>授权管理</template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="机器码">
          <el-input :model-value="authStore.machineId" readonly>
            <template #append>
              <el-button @click="copyMachineId">复制</el-button>
            </template>
          </el-input>
        </el-descriptions-item>
        <el-descriptions-item label="授权状态">
          <el-tag :type="authStore.activated ? 'success' : 'danger'">
            {{ authStore.activated ? '已授权' : '未授权' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="!authStore.activated" style="margin-top: 16px">
        <el-input v-model="licenseCode" type="textarea" :rows="3" placeholder="请粘贴授权码" />
        <el-button type="primary" style="margin-top: 8px" :loading="activating" @click="onActivate">
          验证并激活
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()
const licenseCode = ref('')
const activating = ref(false)

onMounted(() => authStore.checkStatus())

function copyMachineId() {
  navigator.clipboard.writeText(authStore.machineId)
  ElMessage.success('机器码已复制')
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
    ElMessage.error('激活请求失败')
  } finally {
    activating.value = false
  }
}
</script>
