<template>
  <div class="plugin-page">
    <!-- Header -->
    <div class="page-header">
      <h2>{{ pluginInfo.display_name }}</h2>
      <div class="header-actions">
        <el-dropdown v-if="pluginInfo.templates?.length" @command="onLoadTemplate">
          <el-button size="small">加载模板<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="t in pluginInfo.templates" :key="t.name" :command="t.name">{{ t.name }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button v-if="isFileOrganizer" size="small" @click="rulesDialogVisible = true">
          <el-icon><Setting /></el-icon> 规则设置
        </el-button>
        <el-button size="small" @click="historyDialogVisible = true">
          <el-icon><Clock /></el-icon> 执行历史
        </el-button>
      </div>
    </div>

    <!-- File-organizer: onboarding -->
    <el-alert v-if="isFileOrganizer && !formData.rules?.length" type="info" :closable="false" style="margin-bottom: 16px">
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
              <el-dropdown-item v-for="t in pluginInfo.templates" :key="t.name" :command="t.name">{{ t.name }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button size="small" @click="rulesDialogVisible = true">手动配置规则</el-button>
      </div>
    </el-alert>

    <!-- File-organizer: rules summary -->
    <div v-if="isFileOrganizer && formData.rules?.length" class="rules-summary">
      <el-icon><InfoFilled /></el-icon>
      <span>当前规则: {{ formData.rules.length }} 条</span>
      <span v-for="r in formData.rules.filter((r: any) => r.enabled)" :key="r.doc_type" style="margin-left: 4px">
        <el-tag size="small" type="primary">{{ r.doc_type }}</el-tag>
      </span>
      <el-button link size="small" @click="rulesDialogVisible = true" style="margin-left: 8px">修改</el-button>
    </div>

    <!-- Form params (text, select, file) -->
    <el-card v-if="formParams.length" style="margin-top: 16px">
      <el-form label-position="right" label-width="auto" size="default">
        <el-row :gutter="16">
          <el-col v-for="param in formParams" :key="param.name" :span="8">
            <el-form-item :label="param.label">
              <el-input v-if="param.type === 'text'" v-model="formData[param.name]" :placeholder="param.help || ''" />
              <el-select v-else-if="param.type === 'select'" v-model="formData[param.name]" style="width: 100%">
                <el-option v-for="opt in param.options" :key="opt" :label="opt" :value="opt" />
              </el-select>
              <div v-else-if="param.type === 'file'" style="display: flex; gap: 8px; width: 100%">
                <el-input v-model="formData[param.name]" :placeholder="param.help || '文件路径'" />
                <el-upload
                  :auto-upload="true"
                  :show-file-list="false"
                  :action="`/api/plugins/upload?token=${apiToken}`"
                  :on-success="(res: any) => formData[param.name] = res.path"
                  :on-error="() => ElMessage.error('上传失败')"
                  accept=".xlsx,.xls,.csv,.pdf,.doc,.docx"
                >
                  <el-button size="small">选择文件</el-button>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- File-organizer: tasks table -->
    <el-card v-if="isFileOrganizer && tasksParam" style="margin-top: 16px">
      <template #header>
        <span>任务清单</span>
        <span style="color: #999; font-size: 12px; margin-left: 8px">
          点击「添加」新增任务，或「批量导入」从Excel粘贴。点击「关键字配置」列设置各分类的关键词
        </span>
      </template>
      <SchemaTable :schema="tasksParam" v-model="formData.tasks" :rules-data="formData.rules" />
    </el-card>

    <!-- Generic: all table params inline -->
    <template v-if="!isFileOrganizer">
      <el-card v-for="param in tableParams" :key="param.name" style="margin-top: 16px">
        <template #header>
          <span>{{ param.label }}</span>
          <span v-if="param.help" style="color: #999; font-size: 12px; margin-left: 8px">{{ param.help }}</span>
        </template>
        <SchemaTable :schema="param" v-model="formData[param.name]" />
      </el-card>
    </template>

    <!-- Action buttons -->
    <div class="action-bar">
      <template v-if="isFileOrganizer">
        <el-button type="primary" size="large" :loading="running" :disabled="!formData.tasks?.length || !formData.rules?.length" @click="onScan">
          <el-icon><Search /></el-icon> 扫描
        </el-button>
        <el-button type="success" size="large" :loading="running" :disabled="!foundCount" @click="onCopy">
          <el-icon><CopyDocument /></el-icon> 复制 ({{ foundCount }} 个文件)
        </el-button>
      </template>
      <template v-else>
        <el-button type="primary" size="large" :loading="running" @click="onExecute">执行</el-button>
      </template>
      <el-button v-if="running" type="danger" size="large" @click="onCancel">取消</el-button>
    </div>

    <!-- Error display (失败原因展示，所有插件通用) -->
    <el-alert v-if="errorData" type="error" :closable="false" style="margin-top: 16px" show-icon>
      <template #title>{{ friendlyError(errorData).title }}</template>
      <template #default>
        <el-button text size="small" @click="errorDetailVisible = true">查看技术详情</el-button>
      </template>
    </el-alert>

    <!-- Error detail dialog -->
    <el-dialog v-model="errorDetailVisible" title="错误详情" width="720px" destroy-on-close>
      <pre class="error-detail">{{ friendlyError(errorData).detail }}</pre>
      <template #footer>
        <el-button @click="errorDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Progress -->
    <el-progress v-if="running" :percentage="progress.percent" :format="() => progress.message" style="margin-top: 16px" :stroke-width="18" striped striped-flow />

    <!-- File-organizer: scan/copy results -->
    <el-card v-if="isFileOrganizer && plan.length" style="margin-top: 16px">
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
            <el-tag v-if="row.copy_status" :type="row.copy_status === '已复制' ? 'success' : row.copy_status === '用户跳过' ? 'info' : 'danger'" size="small">{{ row.copy_status }}</el-tag>
            <el-tag v-else :type="row.find_status === '已找到' ? 'success' : 'danger'" size="small">{{ row.find_status }}</el-tag>
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
            <el-button v-if="row.copy_status === '已复制' && row.dest_path" link type="primary" size="small" @click="openFolder(row.dest_path)">打开文件夹</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Generic: result display -->
    <div v-if="!isFileOrganizer && resultData" style="margin-top: 16px">
      <el-alert :type="resultData.status === 'success' ? 'success' : 'error'" :closable="false" style="margin-bottom: 16px">
        <template #title>{{ resultData.summary }}</template>
      </el-alert>

      <!-- Bank reconciliation results -->
      <template v-if="isBankReconciliation && resultData.data">
        <el-row :gutter="12" style="margin-bottom: 16px">
          <el-col :span="6"><el-statistic title="银行流水" :value="resultData.data.bank_count || 0" suffix="笔" /></el-col>
          <el-col :span="6"><el-statistic title="日记账" :value="resultData.data.journal_count || 0" suffix="笔" /></el-col>
          <el-col :span="6"><el-statistic title="已匹配" :value="resultData.data.match_summary?.matched || 0" suffix="笔" /></el-col>
          <el-col :span="6"><el-statistic title="匹配率" :value="((resultData.data.match_summary?.match_rate || 0) * 100).toFixed(1)" suffix="%" /></el-col>
        </el-row>

        <!-- Reconciliation statement -->
        <el-card v-if="resultData.data.statement">
          <template #header><span>银行存款余额调节表</span></template>
          <el-row :gutter="20">
            <el-col :span="12">
              <h4 style="margin-top: 0">银行对账单</h4>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="银行对账单余额">{{ formatAmount(resultData.data.statement.bank_side?.bank_balance) }}</el-descriptions-item>
                <el-descriptions-item label="+ 企业已收银行未收">{{ formatAmount(resultData.data.statement.bank_side?.journal_in_unmatched) }}</el-descriptions-item>
                <el-descriptions-item label="- 企业已付银行未付">{{ formatAmount(resultData.data.statement.bank_side?.journal_out_unmatched) }}</el-descriptions-item>
                <el-descriptions-item label="调节后余额"><b>{{ formatAmount(resultData.data.statement.bank_side?.adjusted_balance) }}</b></el-descriptions-item>
              </el-descriptions>
            </el-col>
            <el-col :span="12">
              <h4 style="margin-top: 0">企业日记账</h4>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="日记账余额">{{ formatAmount(resultData.data.statement.journal_side?.journal_balance) }}</el-descriptions-item>
                <el-descriptions-item label="+ 银行已收企业未收">{{ formatAmount(resultData.data.statement.journal_side?.bank_in_unmatched) }}</el-descriptions-item>
                <el-descriptions-item label="- 银行已付企业未付">{{ formatAmount(resultData.data.statement.journal_side?.bank_out_unmatched) }}</el-descriptions-item>
                <el-descriptions-item label="调节后余额"><b>{{ formatAmount(resultData.data.statement.journal_side?.adjusted_balance) }}</b></el-descriptions-item>
              </el-descriptions>
            </el-col>
          </el-row>
          <div style="text-align: center; margin-top: 12px">
            <el-tag :type="resultData.data.statement.is_balanced ? 'success' : 'danger'" size="large">
              {{ resultData.data.statement.is_balanced ? '✓ 调节后余额一致' : '✗ 调节后余额不一致' }}
            </el-tag>
          </div>
        </el-card>

        <!-- Matched pairs -->
        <el-card style="margin-top: 16px" v-if="resultData.data.matched?.length">
          <template #header>已匹配 ({{ resultData.data.matched.length }}笔)</template>
          <el-table :data="resultData.data.matched" size="small" border max-height="300">
            <el-table-column prop="bank_date" label="银行日期" width="110" />
            <el-table-column label="银行金额" width="110">
              <template #default="{ row }">{{ formatAmount(row.bank_amount) }}</template>
            </el-table-column>
            <el-table-column prop="bank_summary" label="银行摘要" show-overflow-tooltip />
            <el-table-column prop="journal_date" label="日记账日期" width="110" />
            <el-table-column label="日记账金额" width="110">
              <template #default="{ row }">{{ formatAmount(row.journal_amount) }}</template>
            </el-table-column>
            <el-table-column prop="journal_summary" label="日记账摘要" show-overflow-tooltip />
            <el-table-column prop="strategy" label="匹配策略" width="120" />
            <el-table-column prop="notes" label="备注" width="120" />
          </el-table>
        </el-card>

        <!-- Unmatched bank -->
        <el-card style="margin-top: 16px" v-if="resultData.data.unmatched_bank?.length">
          <template #header>银行未匹配 ({{ resultData.data.unmatched_bank.length }}笔)</template>
          <el-table :data="resultData.data.unmatched_bank" size="small" border max-height="200">
            <el-table-column prop="date" label="日期" width="110" />
            <el-table-column label="金额" width="110">
              <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="方向" width="60">
              <template #default="{ row }">
                <el-tag :type="row.direction === 'income' ? 'success' : 'danger'" size="small">{{ row.direction === 'income' ? '收入' : '支出' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="summary" label="摘要" show-overflow-tooltip />
          </el-table>
        </el-card>

        <!-- Unmatched journal -->
        <el-card style="margin-top: 16px" v-if="resultData.data.unmatched_journal?.length">
          <template #header>日记账未匹配 ({{ resultData.data.unmatched_journal.length }}笔)</template>
          <el-table :data="resultData.data.unmatched_journal" size="small" border max-height="200">
            <el-table-column prop="date" label="日期" width="110" />
            <el-table-column label="金额" width="110">
              <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="方向" width="60">
              <template #default="{ row }">
                <el-tag :type="row.direction === 'income' ? 'success' : 'danger'" size="small">{{ row.direction === 'income' ? '收入' : '支出' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="summary" label="摘要" show-overflow-tooltip />
          </el-table>
        </el-card>
      </template>

      <!-- Stock price results -->
      <template v-if="isStockPrice && resultData.data">
        <el-row :gutter="12" style="margin-bottom: 16px">
          <el-col :span="6"><el-statistic title="查询总数" :value="resultData.data.summary?.total || 0" suffix="只" /></el-col>
          <el-col :span="6"><el-statistic title="上涨" :value="resultData.data.summary?.up || 0">
            <template #suffix><span style="color: #f56c6c">只</span></template>
          </el-statistic></el-col>
          <el-col :span="6"><el-statistic title="下跌" :value="resultData.data.summary?.down || 0">
            <template #suffix><span style="color: #67c23a">只</span></template>
          </el-statistic></el-col>
          <el-col :span="6"><el-statistic title="异常" :value="resultData.data.summary?.errors || 0" suffix="只" /></el-col>
        </el-row>

        <el-card v-if="resultData.data.rows?.length">
          <el-table :data="resultData.data.rows" size="small" border max-height="400">
            <el-table-column prop="code" label="代码" width="120" />
            <el-table-column prop="name" label="名称" width="100" />
            <el-table-column prop="remark" label="备注" width="100" show-overflow-tooltip />
            <el-table-column label="最新价" width="100">
              <template #default="{ row }">
                <span :style="{color: row.change > 0 ? '#f56c6c' : row.change < 0 ? '#67c23a' : '#333'}">
                  {{ row.current?.toFixed(2) || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="涨跌额" width="90">
              <template #default="{ row }">
                <span :style="{color: row.change > 0 ? '#f56c6c' : row.change < 0 ? '#67c23a' : '#333'}">
                  {{ row.change > 0 ? '+' : '' }}{{ row.change?.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="涨跌幅" width="90">
              <template #default="{ row }">
                <el-tag :type="row.change_pct > 0 ? 'danger' : row.change_pct < 0 ? 'success' : 'info'" size="small">
                  {{ row.change_pct > 0 ? '+' : '' }}{{ row.change_pct }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="open" label="今开" width="90">
              <template #default="{ row }">{{ row.open?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="high" label="最高" width="90">
              <template #default="{ row }">{{ row.high?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="low" label="最低" width="90">
              <template #default="{ row }">{{ row.low?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="成交量" width="100">
              <template #default="{ row }">{{ row.volume ? (row.volume / 10000).toFixed(0) + '万' : '-' }}</template>
            </el-table-column>
            <el-table-column prop="error" label="错误" width="150" show-overflow-tooltip />
          </el-table>
          <div style="margin-top: 8px; color: #909399; font-size: 12px">
            数据来源：新浪财经 | 查询时间：{{ resultData.data.rows?.[0]?.date }} {{ resultData.data.rows?.[0]?.time }}
          </div>
        </el-card>
      </template>
    </div>

    <!-- File-organizer: rules dialog -->
    <el-dialog v-if="isFileOrganizer" v-model="rulesDialogVisible" title="规则设置" width="900px" destroy-on-close>
      <el-alert type="info" :closable="false" style="margin-bottom: 12px">
        <template #title>规则说明</template>
        <p>规则定义了各类文件的搜索方式。配置一次后通常不需要修改，日常只需添加任务。</p>
        <p><b>文件名匹配规则</b>：使用特殊符号匹配文件名。</p>
        <ul style="margin: 4px 0; padding-left: 20px">
          <li><code>*</code> — 匹配任意字符，如 <code>*发票*</code> 匹配所有文件名含"发票"的文件</li>
          <li><code>{文件关键词}</code> — 会在扫描时自动替换为你在任务中设置的文件关键词</li>
          <li><code>{文件分类}</code> — 会在扫描时自动替换为当前规则的分类名（如"发票"、"报关单"）</li>
        </ul>
        <p><b>搜索路径</b>：路径中的 <code>{路径关键词}</code> 会在扫描时自动替换为你在任务中设置的路径关键词。</p>
      </el-alert>
      <SchemaTable v-if="rulesParam" :schema="rulesParam" v-model="formData.rules" />
      <template #footer>
        <el-button @click="rulesDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>

    <!-- History dialog -->
    <el-dialog v-model="historyDialogVisible" title="执行历史" width="780px" destroy-on-close>
      <el-table :data="history" size="small" border v-loading="historyLoading">
        <el-table-column prop="id" label="#" width="60" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : row.status === 'cancelled' ? 'info' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="结果" show-overflow-tooltip />
        <el-table-column prop="created_at" label="执行时间" width="170" />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button v-if="row.status === 'error' && row.error_traceback" link type="primary" size="small" @click="showHistoryError(row.error_traceback)">查看错误</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!history.length && !historyLoading" description="暂无执行记录，执行后将在此显示" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { pluginApi, systemApi } from '@/api'
import { ElMessage } from 'element-plus'
import SchemaTable from '@/components/schema/SchemaTable.vue'
import { friendlyError } from '@/utils/errorMessage'

const route = useRoute()
const pluginName = computed(() => route.path.replace('/plugin/', ''))
const apiToken = computed(() => localStorage.getItem('api_token') || '')

const pluginInfo = ref<any>({})
const formData = ref<any>({})
const running = ref(false)
const progress = ref({ percent: 0, message: '' })
const resultData = ref<any>(null)
const errorData = ref('')               // 失败原因（traceback 或校验消息），空=无错误
const errorDetailVisible = ref(false)   // 错误详情弹窗

// File-organizer specific state
const plan = ref<any[]>([])
const copyDone = ref(false)

// Dialogs
const rulesDialogVisible = ref(false)
const historyDialogVisible = ref(false)
const history = ref<any[]>([])
const historyLoading = ref(false)
const currentTaskId = ref<number | null>(null)

// Computed
const isFileOrganizer = computed(() => pluginName.value === 'file-organizer')
const isBankReconciliation = computed(() => pluginName.value === 'bank-reconciliation')
const isStockPrice = computed(() => pluginName.value === 'stock-price-query')

const formParams = computed(() =>
  pluginInfo.value.params?.filter((p: any) => p.type !== 'table') || []
)
const tableParams = computed(() =>
  isFileOrganizer.value ? [] : (pluginInfo.value.params?.filter((p: any) => p.type === 'table') || [])
)
const tasksParam = computed(() =>
  isFileOrganizer.value ? pluginInfo.value.params?.find((p: any) => p.name === 'tasks') : null
)
const rulesParam = computed(() =>
  pluginInfo.value.params?.find((p: any) => p.name === 'rules')
)

// File-organizer stats
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

function formatAmount(val: any): string {
  if (val == null) return ''
  const n = typeof val === 'number' ? val : parseFloat(String(val).replace(/,/g, ''))
  if (isNaN(n)) return String(val)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// Auto-save（跳过初始加载触发的watch）
let saveTimer: ReturnType<typeof setTimeout> | null = null
let saving = false
let initialized = false
watch(formData, () => {
  if (!initialized || saving) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => saveConfig(), 1000)
}, { deep: true })

async function saveConfig() {
  if (saving) return
  saving = true
  try {
    await pluginApi.saveConfig(pluginName.value, formData.value)
  } catch {
    // silent
  } finally {
    saving = false
  }
}

onMounted(async () => {
  try {
    const { data } = await pluginApi.getInfo(pluginName.value)
    pluginInfo.value = data
    const { data: config } = await pluginApi.getConfig(pluginName.value)
    formData.value = config

    // 标记初始化完成，后续formData变化才触发自动保存
    await new Promise(r => setTimeout(r, 0))
    initialized = true

    // File-organizer: auto-open rules dialog on first use
    if (isFileOrganizer.value && !formData.value.rules?.length && pluginInfo.value.templates?.length) {
      rulesDialogVisible.value = true
    }
  } catch (e: any) {
    ElMessage.error('加载插件信息失败: ' + (e.message || '未知错误'))
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
    ElMessage.error(e.response?.data?.detail || '加载模板失败')
  }
}

// --- File-organizer: Scan + Copy ---

async function onScan() {
  if (!formData.value.tasks?.length) { ElMessage.warning('请先添加任务'); return }
  if (!formData.value.rules?.length) { ElMessage.warning('请先配置规则'); return }
  running.value = true
  progress.value = { percent: 0, message: '扫描中...' }
  plan.value = []
  copyDone.value = false
  errorData.value = ''
  currentTaskId.value = null
  try {
    const { data } = await pluginApi.execute(pluginName.value, { ...formData.value, action: 'scan' })
    currentTaskId.value = data.task_id
    await pollUntilDone(data.task_id)
  } catch (e: any) {
    running.value = false
    const detail = e.response?.data?.detail || '扫描失败'
    errorData.value = detail
    ElMessage.error(friendlyError(detail).title)
  }
}

async function onCopy() {
  running.value = true
  progress.value = { percent: 0, message: '复制中...' }
  errorData.value = ''
  currentTaskId.value = null
  try {
    const { data } = await pluginApi.execute(pluginName.value, { ...formData.value, action: 'copy', plan: plan.value })
    currentTaskId.value = data.task_id
    await pollUntilDone(data.task_id)
    copyDone.value = true
  } catch (e: any) {
    running.value = false
    const detail = e.response?.data?.detail || '复制失败'
    errorData.value = detail
    ElMessage.error(friendlyError(detail).title)
  }
}

// --- Generic: Execute ---

async function onExecute() {
  running.value = true
  progress.value = { percent: 0, message: '执行中...' }
  resultData.value = null
  errorData.value = ''
  currentTaskId.value = null
  try {
    const { data } = await pluginApi.execute(pluginName.value, formData.value)
    currentTaskId.value = data.task_id
    await pollUntilDone(data.task_id)
  } catch (e: any) {
    running.value = false
    const detail = e.response?.data?.detail || '执行失败'
    errorData.value = detail
    ElMessage.error(friendlyError(detail).title)
  }
}

// --- Shared: Poll status ---

async function pollUntilDone(taskId: number) {
  for (let i = 0; i < 600; i++) {
    await new Promise(r => setTimeout(r, 1000))
    try {
      const { data } = await pluginApi.getStatus(pluginName.value, taskId)
      progress.value = {
        percent: data.progress_percent || 0,
        message: data.progress_message || '',
      }
      if (['success', 'error', 'cancelled'].includes(data.status)) {
        running.value = false
        if (data.status === 'success' && data.result) {
          errorData.value = ''
          if (isFileOrganizer.value) {
            if (data.result.data?.plan) plan.value = data.result.data.plan
            if (data.result.data?.tasks) formData.value.tasks = data.result.data.tasks
          } else {
            resultData.value = data.result
          }
          ElMessage.success(data.result.summary || data.progress_message)
        } else if (data.status === 'error') {
          // 优先用 error_traceback（子进程异常），其次用 progress_message（业务级 error，如"请先添加任务和规则"）
          const tb = data.error_traceback || data.progress_message || '执行失败'
          errorData.value = tb
          ElMessage.error(friendlyError(tb).title)
        }
        return
      }
    } catch {
      // continue polling
    }
  }
  running.value = false
  ElMessage.warning('执行超时，请查看历史记录')
}

async function onCancel() {
  if (!currentTaskId.value) return
  try {
    await pluginApi.cancel(pluginName.value, currentTaskId.value)
    ElMessage.info('已发送取消请求')
  } catch {
    ElMessage.error('取消失败')
  }
}

// --- History ---

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

watch(historyDialogVisible, (v) => { if (v) loadHistory() })

function showHistoryError(traceback: string) {
  errorData.value = traceback
  errorDetailVisible.value = true
}

async function openFolder(filePath: string) {
  const sepIdx = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'))
  const dir = sepIdx >= 0 ? filePath.substring(0, sepIdx) : filePath
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
.error-detail {
  max-height: 400px;
  overflow: auto;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Menlo', 'Consolas', monospace;
  margin: 0;
}
</style>
