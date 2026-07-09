<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import {
  Play,
  Square,
  RotateCcw,
  Save,
  UserX,
  Ban,
  Megaphone,
  RefreshCw,
} from 'lucide-vue-next'

const players = ref<string[]>([])
const announceMsg = ref('')
const kickPlayer = ref('')
const kickReason = ref('')
const banPlayer = ref('')
const banReason = ref('')
const loading = ref({ start: false, stop: false, restart: false, save: false })
const serverRunning = ref(false)

async function fetchStatus() {
  try {
    const { data } = await api.get('/server/status')
    serverRunning.value = data.running
  } catch { /* ignore */ }
}

async function fetchPlayers() {
  try {
    const { data } = await api.get('/commands/players')
    players.value = data.players || []
  } catch { /* ignore */ }
}

async function startServer() {
  loading.value.start = true
  try {
    const { data } = await api.post('/server/start')
    if (!data.success) alert(data.error || '启动失败')
    await fetchStatus()
  } catch (e: any) { alert(e.message) }
  finally { loading.value.start = false }
}

async function stopServer() {
  loading.value.stop = true
  try {
    const { data } = await api.post('/server/stop')
    if (!data.success) alert(data.error || '停止失败')
    await fetchStatus()
  } catch (e: any) { alert(e.message) }
  finally { loading.value.stop = false }
}

async function restartServer() {
  loading.value.restart = true
  try {
    const { data } = await api.post('/server/restart')
    if (!data.success) alert(data.error || '重启失败')
    await fetchStatus()
  } catch (e: any) { alert(e.message) }
  finally { loading.value.restart = false }
}

async function saveServer() {
  loading.value.save = true
  try {
    const { data } = await api.post('/server/save')
    if (!data.success) alert(data.error || '保存失败')
    else alert('保存指令已发送')
  } catch (e: any) { alert(e.message) }
  finally { loading.value.save = false }
}

async function doKick() {
  if (!kickPlayer.value.trim()) return alert('请输入玩家名称')
  try {
    const { data } = await api.post('/commands/kick', { player: kickPlayer.value, reason: kickReason.value })
    if (data.success) { kickPlayer.value = ''; kickReason.value = ''; alert('已踢出玩家') }
    else alert(data.error || '踢出失败')
  } catch (e: any) { alert(e.message) }
}

async function doBan() {
  if (!banPlayer.value.trim()) return alert('请输入玩家名称')
  try {
    const { data } = await api.post('/commands/ban', { player: banPlayer.value, reason: banReason.value })
    if (data.success) { banPlayer.value = ''; banReason.value = ''; alert('已封禁玩家') }
    else alert(data.error || '封禁失败')
  } catch (e: any) { alert(e.message) }
}

async function doAnnounce() {
  if (!announceMsg.value.trim()) return alert('请输入公告内容')
  try {
    const { data } = await api.post('/commands/announce', { message: announceMsg.value })
    if (data.success) { announceMsg.value = ''; alert('公告已发送') }
    else alert(data.error || '发送失败')
  } catch (e: any) { alert(e.message) }
}

onMounted(() => {
  fetchStatus()
  fetchPlayers()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Server Control -->
    <div class="card">
      <h3 class="font-display font-semibold text-lg mb-4 flex items-center gap-2">
        <Play class="w-5 h-5 text-factorio-accent" />
        服务器控制
      </h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <button @click="startServer" :disabled="loading.start || serverRunning" class="btn-success justify-center py-4">
          <Play class="w-5 h-5" />
          <span>{{ loading.start ? '启动中...' : '启动服务器' }}</span>
        </button>
        <button @click="stopServer" :disabled="loading.stop || !serverRunning" class="btn-danger justify-center py-4">
          <Square class="w-5 h-5" />
          <span>{{ loading.stop ? '停止中...' : '停止服务器' }}</span>
        </button>
        <button @click="restartServer" :disabled="loading.restart || !serverRunning" class="btn-primary justify-center py-4">
          <RotateCcw class="w-5 h-5" />
          <span>{{ loading.restart ? '重启中...' : '重启服务器' }}</span>
        </button>
        <button @click="saveServer" :disabled="loading.save || !serverRunning" class="btn-info justify-center py-4">
          <Save class="w-5 h-5" />
          <span>{{ loading.save ? '保存中...' : '强制保存' }}</span>
        </button>
      </div>
    </div>

    <!-- Player Management -->
    <div class="card">
      <h3 class="font-display font-semibold text-lg mb-4 flex items-center gap-2">
        <UserX class="w-5 h-5 text-factorio-accent" />
        玩家管理
        <button @click="fetchPlayers" class="btn-ghost ml-auto text-xs px-2 py-1">
          <RefreshCw class="w-3.5 h-3.5" />
          刷新
        </button>
      </h3>

      <!-- Online Players -->
      <div class="mb-4">
        <p class="text-sm text-factorio-text-muted mb-2">在线玩家 ({{ players.length }})</p>
        <div v-if="players.length === 0" class="text-sm text-factorio-text-muted py-2">暂无在线玩家</div>
        <div v-else class="flex flex-wrap gap-2">
          <span
            v-for="p in players"
            :key="p"
            class="badge-info"
          >{{ p }}</span>
        </div>
      </div>

      <!-- Kick -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div class="space-y-2">
          <p class="text-sm font-medium text-factorio-text-muted">踢出玩家</p>
          <div class="flex gap-2">
            <input v-model="kickPlayer" class="input flex-1" placeholder="玩家名称" />
            <input v-model="kickReason" class="input flex-1" placeholder="原因（可选）" />
            <button @click="doKick" class="btn-danger shrink-0">
              <UserX class="w-4 h-4" />
              踢出
            </button>
          </div>
        </div>
        <div class="space-y-2">
          <p class="text-sm font-medium text-factorio-text-muted">封禁玩家</p>
          <div class="flex gap-2">
            <input v-model="banPlayer" class="input flex-1" placeholder="玩家名称" />
            <input v-model="banReason" class="input flex-1" placeholder="原因（可选）" />
            <button @click="doBan" class="btn-danger shrink-0">
              <Ban class="w-4 h-4" />
              封禁
            </button>
          </div>
        </div>
      </div>

      <!-- Announce -->
      <div class="space-y-2">
        <p class="text-sm font-medium text-factorio-text-muted">服务器公告</p>
        <div class="flex gap-2">
          <input v-model="announceMsg" class="input flex-1" placeholder="输入公告内容..." @keyup.enter="doAnnounce" />
          <button @click="doAnnounce" class="btn-info shrink-0">
            <Megaphone class="w-4 h-4" />
            发送
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
