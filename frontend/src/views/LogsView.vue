<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import api from '@/api'
import { Search, Pause, Play, Download, RefreshCw, ChevronDown } from 'lucide-vue-next'

const logLines = ref<string[]>([])
const logFiles = ref<{ filename: string; size: number; modified: number }[]>([])
const selectedFile = ref('')
const keyword = ref('')
const paused = ref(false)
const autoScroll = ref(true)
const logContainer = ref<HTMLElement | null>(null)
let ws: WebSocket | null = null

async function fetchLogFiles() {
  try {
    const { data } = await api.get('/logs/files')
    logFiles.value = data.files || []
  } catch { /* ignore */ }
}

async function fetchLogContent() {
  try {
    const params: any = { limit: 500 }
    if (selectedFile.value) params.file = selectedFile.value
    if (keyword.value) params.keyword = keyword.value
    const { data } = await api.get('/logs/content', { params })
    logLines.value = data.lines || []
    await nextTick()
    scrollToBottom()
  } catch { /* ignore */ }
}

function scrollToBottom() {
  if (autoScroll.value && logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

function connectWs() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${proto}//${location.host}/api/logs/stream`
  ws = new WebSocket(url)
  ws.onmessage = (e) => {
    if (e.data && !paused.value) {
      logLines.value.push(e.data)
      if (logLines.value.length > 2000) {
        logLines.value = logLines.value.slice(-2000)
      }
      nextTick(scrollToBottom)
    }
  }
  ws.onclose = () => {
    setTimeout(connectWs, 5000)
  }
}

function togglePause() {
  paused.value = !paused.value
}

function formatLogLine(line: string): { time: string; level: string; msg: string; cls: string } {
  const timeMatch = line.match(/(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/)
  const time = timeMatch ? timeMatch[1] : ''
  let level = ''
  let cls = 'text-factorio-text'
  if (/error|exception|failed|crash/i.test(line)) {
    level = 'ERROR'
    cls = 'text-factorio-danger'
  } else if (/warn|warning/i.test(line)) {
    level = 'WARN'
    cls = 'text-factorio-accent-light'
  } else if (/info/i.test(line)) {
    level = 'INFO'
    cls = 'text-factorio-text'
  } else if (/verbose|debug/i.test(line)) {
    level = 'DEBUG'
    cls = 'text-factorio-text-muted'
  }
  return { time, level, msg: line, cls }
}

onMounted(() => {
  fetchLogFiles()
  fetchLogContent()
  connectWs()
})

onUnmounted(() => {
  if (ws) ws.close()
})
</script>

<template>
  <div class="space-y-4 h-full flex flex-col">
    <!-- Toolbar -->
    <div class="card flex flex-wrap items-center gap-3 shrink-0">
      <div class="flex items-center gap-2 flex-1 min-w-[200px]">
        <Search class="w-4 h-4 text-factorio-text-muted" />
        <input
          v-model="keyword"
          class="input flex-1"
          placeholder="搜索日志..."
          @keyup.enter="fetchLogContent"
        />
      </div>

      <select v-model="selectedFile" class="input min-w-[180px]" @change="fetchLogContent">
        <option value="">实时日志</option>
        <option v-for="f in logFiles" :key="f.filename" :value="f.filename">
          {{ f.filename }}
        </option>
      </select>

      <button @click="fetchLogContent" class="btn-ghost">
        <RefreshCw class="w-4 h-4" />
        刷新
      </button>

      <button @click="togglePause" :class="[paused ? 'btn-success' : 'btn-ghost']">
        <component :is="paused ? Play : Pause" class="w-4 h-4" />
        {{ paused ? '继续' : '暂停' }}
      </button>

      <label class="flex items-center gap-2 text-sm text-factorio-text-muted cursor-pointer">
        <input type="checkbox" v-model="autoScroll" class="rounded" />
        自动滚动
      </label>
    </div>

    <!-- Log Content -->
    <div
      ref="logContainer"
      class="card flex-1 overflow-y-auto bg-[#0a0a14] border-factorio-border font-mono text-xs leading-relaxed min-h-0"
    >
      <div v-if="logLines.length === 0" class="text-factorio-text-muted text-center py-10">
        暂无日志输出，请启动服务器...
      </div>
      <div v-for="(line, i) in logLines" :key="i" class="px-3 py-0.5 hover:bg-white/[0.03]">
        <span
          :class="formatLogLine(line).cls"
          class="whitespace-pre-wrap break-all"
        >{{ line }}</span>
      </div>
    </div>
  </div>
</template>
