<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import api from '@/api'
import {
  Play,
  Square,
  RotateCcw,
  Save,
  Users,
  Clock,
  HardDrive,
  Cpu,
  MemoryStick,
  Activity,
} from 'lucide-vue-next'

interface ServerStatus {
  running: boolean
  uptime_seconds: number
  online_players: string[]
  current_save: string
  pid: number | null
}

interface SystemResources {
  cpu_percent: number
  memory_percent: number
  memory_used_mb: number
  memory_total_mb: number
  disk_percent: number
  disk_free_gb: number
  disk_total_gb: number
}

const status = ref<ServerStatus>({ running: false, uptime_seconds: 0, online_players: [], current_save: '', pid: null })
const systemRes = ref<SystemResources>({ cpu_percent: 0, memory_percent: 0, memory_used_mb: 0, memory_total_mb: 0, disk_percent: 0, disk_free_gb: 0, disk_total_gb: 0 })
const loading = ref({ start: false, stop: false, restart: false, save: false })
let ws: WebSocket | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

const uptimeStr = computed(() => {
  const s = status.value.uptime_seconds
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return `${h}h ${m}m ${sec}s`
})

function formatSize(mb: number) {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`
  return `${mb.toFixed(0)} MB`
}

async function fetchStatus() {
  try {
    const { data } = await api.get('/server/status')
    status.value = data
  } catch { /* ignore */ }
}

async function fetchResources() {
  try {
    const { data } = await api.get('/server/resources')
    systemRes.value = data.system
  } catch { /* ignore */ }
}

async function startServer() {
  loading.value.start = true
  try {
    const { data } = await api.post('/server/start')
    if (data.success) {
      await fetchStatus()
    } else {
      alert(data.error || '启动失败')
    }
  } catch (e: any) {
    alert(e.message || '启动失败')
  } finally {
    loading.value.start = false
  }
}

async function stopServer() {
  loading.value.stop = true
  try {
    const { data } = await api.post('/server/stop')
    if (!data.success) alert(data.error || '停止失败')
    await fetchStatus()
  } catch (e: any) {
    alert(e.message || '停止失败')
  } finally {
    loading.value.stop = false
  }
}

async function restartServer() {
  loading.value.restart = true
  try {
    const { data } = await api.post('/server/restart')
    if (!data.success) alert(data.error || '重启失败')
    await fetchStatus()
  } catch (e: any) {
    alert(e.message || '重启失败')
  } finally {
    loading.value.restart = false
  }
}

async function saveServer() {
  loading.value.save = true
  try {
    const { data } = await api.post('/server/save')
    if (!data.success) alert(data.error || '保存失败')
  } catch (e: any) {
    alert(e.message || '保存失败')
  } finally {
    loading.value.save = false
  }
}

function connectWs() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${proto}//${location.host}/api/server/ws/status`
  ws = new WebSocket(url)
  ws.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data)
      if (d.server) status.value = d.server
      if (d.system) systemRes.value = d.system
    } catch { /* ignore */ }
  }
  ws.onclose = () => {
    setTimeout(connectWs, 5000)
  }
}

onMounted(() => {
  fetchStatus()
  fetchResources()
  pollTimer = setInterval(() => {
    fetchStatus()
    fetchResources()
  }, 10000)
  connectWs()
})

onUnmounted(() => {
  if (ws) ws.close()
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Status Card -->
    <div class="card glow-accent">
      <div class="flex flex-col lg:flex-row lg:items-center gap-6">
        <div class="flex items-center gap-4">
          <div
            :class="[
              'w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-500',
              status.running
                ? 'bg-factorio-success/20 glow-success'
                : 'bg-factorio-danger/20 glow-danger'
            ]"
          >
            <Activity
              :class="[
                'w-8 h-8 transition-colors',
                status.running ? 'text-factorio-success' : 'text-factorio-danger'
              ]"
            />
          </div>
          <div>
            <h3 class="font-display font-bold text-2xl">
              {{ status.running ? '运行中' : '已停止' }}
            </h3>
            <p class="text-factorio-text-muted text-sm mt-0.5">
              <template v-if="status.running">
                PID: {{ status.pid }} · 运行时长: {{ uptimeStr }}
              </template>
              <template v-else>
                服务器未启动
              </template>
            </p>
          </div>
        </div>

        <div class="flex-1" />

        <!-- Quick Actions -->
        <div class="flex flex-wrap gap-3">
          <button
            v-if="!status.running"
            @click="startServer"
            :disabled="loading.start"
            class="btn-success"
          >
            <Play class="w-4 h-4" />
            {{ loading.start ? '启动中...' : '启动' }}
          </button>
          <button
            v-if="status.running"
            @click="stopServer"
            :disabled="loading.stop"
            class="btn-danger"
          >
            <Square class="w-4 h-4" />
            {{ loading.stop ? '停止中...' : '停止' }}
          </button>
          <button
            v-if="status.running"
            @click="restartServer"
            :disabled="loading.restart"
            class="btn-primary"
          >
            <RotateCcw class="w-4 h-4" />
            {{ loading.restart ? '重启中...' : '重启' }}
          </button>
          <button
            v-if="status.running"
            @click="saveServer"
            :disabled="loading.save"
            class="btn-info"
          >
            <Save class="w-4 h-4" />
            {{ loading.save ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Info Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="card flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-factorio-accent/15 flex items-center justify-center">
          <Save class="w-6 h-6 text-factorio-accent" />
        </div>
        <div>
          <p class="text-factorio-text-muted text-xs uppercase tracking-wider">当前存档</p>
          <p class="font-display font-semibold text-lg mt-0.5">{{ status.current_save || '—' }}</p>
        </div>
      </div>

      <div class="card flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-factorio-info/15 flex items-center justify-center">
          <Users class="w-6 h-6 text-factorio-info" />
        </div>
        <div>
          <p class="text-factorio-text-muted text-xs uppercase tracking-wider">在线玩家</p>
          <p class="font-display font-semibold text-lg mt-0.5">{{ status.online_players.length }}</p>
          <p v-if="status.online_players.length" class="text-xs text-factorio-text-muted mt-0.5">
            {{ status.online_players.join(', ') }}
          </p>
        </div>
      </div>

      <div class="card flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-factorio-success/15 flex items-center justify-center">
          <Clock class="w-6 h-6 text-factorio-success" />
        </div>
        <div>
          <p class="text-factorio-text-muted text-xs uppercase tracking-wider">运行时长</p>
          <p class="font-display font-semibold text-lg mt-0.5">{{ status.running ? uptimeStr : '—' }}</p>
        </div>
      </div>
    </div>

    <!-- Resource Monitor -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="card">
        <div class="flex items-center gap-3 mb-3">
          <Cpu class="w-5 h-5 text-factorio-accent" />
          <span class="text-sm font-medium">CPU</span>
        </div>
        <div class="relative w-full h-3 bg-factorio-bg rounded-full overflow-hidden">
          <div
            class="absolute inset-y-0 left-0 bg-factorio-accent rounded-full transition-all duration-700"
            :style="{ width: `${systemRes.cpu_percent}%` }"
          />
        </div>
        <p class="text-right text-sm text-factorio-text-muted mt-1">{{ systemRes.cpu_percent }}%</p>
      </div>

      <div class="card">
        <div class="flex items-center gap-3 mb-3">
          <MemoryStick class="w-5 h-5 text-factorio-info" />
          <span class="text-sm font-medium">内存</span>
        </div>
        <div class="relative w-full h-3 bg-factorio-bg rounded-full overflow-hidden">
          <div
            class="absolute inset-y-0 left-0 bg-factorio-info rounded-full transition-all duration-700"
            :style="{ width: `${systemRes.memory_percent}%` }"
          />
        </div>
        <p class="text-right text-sm text-factorio-text-muted mt-1">
          {{ formatSize(systemRes.memory_used_mb) }} / {{ formatSize(systemRes.memory_total_mb) }}
        </p>
      </div>

      <div class="card">
        <div class="flex items-center gap-3 mb-3">
          <HardDrive class="w-5 h-5 text-factorio-success" />
          <span class="text-sm font-medium">磁盘</span>
        </div>
        <div class="relative w-full h-3 bg-factorio-bg rounded-full overflow-hidden">
          <div
            class="absolute inset-y-0 left-0 bg-factorio-success rounded-full transition-all duration-700"
            :style="{ width: `${systemRes.disk_percent}%` }"
          />
        </div>
        <p class="text-right text-sm text-factorio-text-muted mt-1">
          {{ systemRes.disk_free_gb.toFixed(1) }} GB 可用 / {{ systemRes.disk_total_gb.toFixed(1) }} GB
        </p>
      </div>
    </div>
  </div>
</template>
