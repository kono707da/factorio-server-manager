<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import {
  Download,
  RefreshCw,
  Package,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-vue-next'

interface VersionInfo {
  current_version: string
  install_path: string
  installed_at: string
  binary_exists: boolean
}

interface LatestInfo {
  stable: string
  experimental: string
  error?: string
}

interface InstallStatus {
  downloading: boolean
  progress: number
  version: string
  error: string
}

const current = ref<VersionInfo>({ current_version: '', install_path: '', installed_at: '', binary_exists: false })
const latest = ref<LatestInfo>({ stable: '', experimental: '' })
const installStatus = ref<InstallStatus>({ downloading: false, progress: 0, version: '', error: '' })
const checking = ref(false)
const installing = ref(false)
const userTriggered = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchCurrent() {
  try {
    const { data } = await api.get('/versions/current')
    current.value = data
  } catch { /* ignore */ }
}

async function checkLatest() {
  checking.value = true
  try {
    const { data } = await api.get('/versions/latest')
    latest.value = data
  } catch (e: any) {
    latest.value = { stable: '', experimental: '', error: e.message }
  } finally {
    checking.value = false
  }
}

async function installVersion(version: string, channel: string) {
  if (!confirm(`确定要安装 Factorio ${version} (${channel}) 吗？\n\n安装过程中服务器将停止运行，请确保已保存游戏进度。`)) return
  installing.value = true
  userTriggered.value = true
  installStatus.value = { downloading: true, progress: 0, version, error: '' }
  startPolling()
  try {
    await api.post('/versions/install', { version, channel })
  } catch (e: any) {
    installStatus.value.downloading = false
    installing.value = false
    alert(e.message || '启动下载失败')
  }
}

function pollInstallStatus() {
  api.get('/versions/install-status').then(({ data }) => {
    installStatus.value = data
    if (!data.downloading) {
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
      installing.value = false
      if (userTriggered.value) {
        userTriggered.value = false
        if (data.error) {
          alert(`安装失败: ${data.error}`)
        } else if (data.progress >= 100) {
          alert(`Factorio ${data.version} 安装成功！`)
          fetchCurrent()
        }
      }
    }
  }).catch(() => {})
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(pollInstallStatus, 2000)
}

onMounted(async () => {
  fetchCurrent()
  checkLatest()
  await pollInstallStatus()
  if (installStatus.value.downloading) {
    installing.value = true
    startPolling()
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Current Version -->
    <div class="card">
      <h3 class="font-display font-semibold text-lg mb-4 flex items-center gap-2">
        <Package class="w-5 h-5 text-factorio-accent" />
        当前版本
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <p class="text-sm text-factorio-text-muted mb-1">版本号</p>
          <p class="font-display font-bold text-2xl">
            {{ current.current_version || '未安装' }}
          </p>
        </div>
        <div>
          <p class="text-sm text-factorio-text-muted mb-1">安装路径</p>
          <p class="font-mono text-sm break-all">{{ current.install_path || '—' }}</p>
        </div>
        <div>
          <p class="text-sm text-factorio-text-muted mb-1">二进制文件</p>
          <div class="flex items-center gap-2">
            <component
              :is="current.binary_exists ? CheckCircle : AlertCircle"
              :class="current.binary_exists ? 'text-factorio-success' : 'text-factorio-danger'"
              class="w-5 h-5"
            />
            <span :class="current.binary_exists ? 'text-factorio-success' : 'text-factorio-danger'">
              {{ current.binary_exists ? '已找到' : '未找到' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Latest Version -->
    <div class="card">
      <h3 class="font-display font-semibold text-lg mb-4 flex items-center gap-2">
        <RefreshCw class="w-5 h-5 text-factorio-accent" />
        可用版本
        <button @click="checkLatest" :disabled="checking" class="btn-ghost ml-auto text-xs px-2 py-1">
          <RefreshCw :class="{ 'animate-spin': checking }" class="w-3.5 h-3.5" />
          {{ checking ? '检查中...' : '检查更新' }}
        </button>
      </h3>

      <div v-if="latest.error" class="text-factorio-danger text-sm mb-4">
        {{ latest.error }}
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Stable -->
        <div class="card bg-factorio-bg border-factorio-border">
          <div class="flex items-center justify-between mb-3">
            <div>
              <p class="text-xs text-factorio-text-muted uppercase tracking-wider">稳定版</p>
              <p class="font-display font-bold text-xl mt-1">{{ latest.stable || '—' }}</p>
            </div>
            <span
              v-if="latest.stable && latest.stable === current.current_version"
              class="badge-success"
            >当前版本</span>
          </div>
          <button
            v-if="latest.stable && latest.stable !== current.current_version"
            @click="installVersion(latest.stable, 'stable')"
            :disabled="installing || installStatus.downloading"
            class="btn-success w-full justify-center"
          >
            <Download class="w-4 h-4" />
            {{ installing ? '安装中...' : '安装稳定版' }}
          </button>
        </div>

        <!-- Experimental -->
        <div class="card bg-factorio-bg border-factorio-border">
          <div class="flex items-center justify-between mb-3">
            <div>
              <p class="text-xs text-factorio-text-muted uppercase tracking-wider">实验版</p>
              <p class="font-display font-bold text-xl mt-1">{{ latest.experimental || '—' }}</p>
            </div>
            <span
              v-if="latest.experimental && latest.experimental === current.current_version"
              class="badge-success"
            >当前版本</span>
          </div>
          <button
            v-if="latest.experimental && latest.experimental !== current.current_version"
            @click="installVersion(latest.experimental, 'experimental')"
            :disabled="installing || installStatus.downloading"
            class="btn-primary w-full justify-center"
          >
            <Download class="w-4 h-4" />
            {{ installing ? '安装中...' : '安装实验版' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Install Progress -->
    <div v-if="installStatus.downloading" class="card">
      <h3 class="font-display font-semibold text-lg mb-4 flex items-center gap-2">
        <Loader2 class="w-5 h-5 text-factorio-accent animate-spin" />
        下载安装中...
      </h3>
      <div class="space-y-2">
        <div class="flex justify-between text-sm">
          <span>Factorio {{ installStatus.version }}</span>
          <span>{{ installStatus.progress }}%</span>
        </div>
        <div class="w-full h-3 bg-factorio-bg rounded-full overflow-hidden">
          <div
            class="h-full bg-factorio-accent rounded-full transition-all duration-500"
            :style="{ width: `${installStatus.progress}%` }"
          />
        </div>
      </div>
    </div>
  </div>
</template>
