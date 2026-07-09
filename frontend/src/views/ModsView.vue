<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/api'
import { Package, Upload, Trash2, Download, Power, PowerOff, CheckCircle, XCircle } from 'lucide-vue-next'

interface ModInfo {
  filename: string
  name: string
  version: string
  title: string
  author: string
  description: string
  factorio_version: string
  enabled: boolean
  size: number
  modified: string
}

const mods = ref<ModInfo[]>([])
const loading = ref(false)
const uploading = ref(false)
const searchQuery = ref('')

const filteredMods = computed(() => {
  if (!searchQuery.value) return mods.value
  const q = searchQuery.value.toLowerCase()
  return mods.value.filter(m =>
    m.name.toLowerCase().includes(q) ||
    m.title.toLowerCase().includes(q) ||
    m.author.toLowerCase().includes(q)
  )
})

const enabledCount = computed(() => mods.value.filter(m => m.enabled).length)
const disabledCount = computed(() => mods.value.filter(m => !m.enabled).length)

async function fetchMods() {
  loading.value = true
  try {
    const { data } = await api.get('/mods')
    mods.value = data.mods
  } catch (e: any) {
    alert(e.message || '获取 Mod 列表失败')
  } finally {
    loading.value = false
  }
}

async function uploadMod(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  uploading.value = true
  for (const file of Array.from(input.files)) {
    if (!file.name.endsWith('.zip')) {
      alert(`${file.name} 不是 .zip 文件，已跳过`)
      continue
    }
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.post('/mods/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })
    } catch (e: any) {
      alert(`上传 ${file.name} 失败: ${e.message}`)
    }
  }
  input.value = ''
  uploading.value = false
  await fetchMods()
}

async function deleteMod(mod: ModInfo) {
  if (!confirm(`确定要删除 ${mod.title || mod.name} 吗？`)) return
  try {
    await api.delete(`/mods/${mod.filename}`)
    await fetchMods()
  } catch (e: any) {
    alert(e.message || '删除失败')
  }
}

async function toggleMod(mod: ModInfo) {
  try {
    await api.post('/mods/toggle', { filename: mod.filename, enabled: !mod.enabled })
    mod.enabled = !mod.enabled
  } catch (e: any) {
    alert(e.message || '操作失败')
  }
}

async function toggleAll(enabled: boolean) {
  try {
    await api.post(`/mods/toggle-all?enabled=${enabled}`)
    await fetchMods()
  } catch (e: any) {
    alert(e.message || '批量操作失败')
  }
}

function downloadMod(mod: ModInfo) {
  window.open(`/api/mods/download/${mod.filename}`, '_blank')
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onMounted(fetchMods)
</script>

<template>
  <div class="space-y-6">
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-display font-semibold text-lg flex items-center gap-2">
          <Package class="w-5 h-5 text-factorio-accent" />
          Mod 管理
        </h3>
        <div class="flex items-center gap-2">
          <button @click="toggleAll(true)" class="btn-secondary text-sm" :disabled="loading">
            <Power class="w-4 h-4" />
            全部启用
          </button>
          <button @click="toggleAll(false)" class="btn-secondary text-sm" :disabled="loading">
            <PowerOff class="w-4 h-4" />
            全部禁用
          </button>
        </div>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-3 gap-4 mb-4">
        <div class="bg-factorio-card rounded-lg p-3 text-center">
          <p class="text-2xl font-bold text-factorio-text">{{ mods.length }}</p>
          <p class="text-xs text-factorio-text-muted">总数</p>
        </div>
        <div class="bg-factorio-card rounded-lg p-3 text-center">
          <p class="text-2xl font-bold text-factorio-success">{{ enabledCount }}</p>
          <p class="text-xs text-factorio-text-muted">已启用</p>
        </div>
        <div class="bg-factorio-card rounded-lg p-3 text-center">
          <p class="text-2xl font-bold text-factorio-text-muted">{{ disabledCount }}</p>
          <p class="text-xs text-factorio-text-muted">已禁用</p>
        </div>
      </div>

      <!-- Search & Upload -->
      <div class="flex flex-col sm:flex-row gap-3 mb-4">
        <input
          v-model="searchQuery"
          class="input flex-1"
          placeholder="搜索 Mod 名称、作者..."
        />
        <label class="btn-primary cursor-pointer whitespace-nowrap" :class="{ 'opacity-50': uploading }">
          <Upload class="w-4 h-4" />
          {{ uploading ? '上传中...' : '上传 Mod' }}
          <input type="file" accept=".zip" multiple class="hidden" @change="uploadMod" :disabled="uploading" />
        </label>
      </div>

      <!-- Mod List -->
      <div v-if="loading" class="text-center py-8 text-factorio-text-muted">
        加载中...
      </div>
      <div v-else-if="filteredMods.length === 0" class="text-center py-8 text-factorio-text-muted">
        <Package class="w-12 h-12 mx-auto mb-2 opacity-30" />
        <p>{{ searchQuery ? '没有匹配的 Mod' : '暂无 Mod，点击上方按钮上传' }}</p>
      </div>
      <div v-else class="space-y-2">
        <div
          v-for="mod in filteredMods"
          :key="mod.filename"
          class="bg-factorio-card rounded-lg p-4 flex items-start gap-4"
          :class="{ 'opacity-50': !mod.enabled }"
        >
          <!-- Status icon -->
          <div class="pt-1">
            <CheckCircle v-if="mod.enabled" class="w-5 h-5 text-factorio-success" />
            <XCircle v-else class="w-5 h-5 text-factorio-text-muted" />
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-medium text-factorio-text">{{ mod.title || mod.name }}</span>
              <span class="text-xs px-2 py-0.5 rounded bg-factorio-bg text-factorio-text-muted">v{{ mod.version }}</span>
              <span v-if="mod.factorio_version" class="text-xs px-2 py-0.5 rounded bg-factorio-bg text-factorio-text-muted">Factorio {{ mod.factorio_version }}</span>
              <span v-if="mod.author" class="text-xs text-factorio-text-muted">by {{ mod.author }}</span>
            </div>
            <p v-if="mod.description" class="text-sm text-factorio-text-muted mt-1 line-clamp-2">{{ mod.description }}</p>
            <div class="flex items-center gap-3 mt-1 text-xs text-factorio-text-muted">
              <span>{{ formatSize(mod.size) }}</span>
              <span>{{ new Date(mod.modified).toLocaleString() }}</span>
              <span class="font-mono">{{ mod.filename }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <button
              @click="toggleMod(mod)"
              class="p-2 rounded-lg hover:bg-factorio-bg text-factorio-text-muted hover:text-factorio-text transition-colors"
              :title="mod.enabled ? '禁用' : '启用'"
            >
              <Power v-if="!mod.enabled" class="w-4 h-4" />
              <PowerOff v-else class="w-4 h-4" />
            </button>
            <button
              @click="downloadMod(mod)"
              class="p-2 rounded-lg hover:bg-factorio-bg text-factorio-text-muted hover:text-factorio-text transition-colors"
              title="下载"
            >
              <Download class="w-4 h-4" />
            </button>
            <button
              @click="deleteMod(mod)"
              class="p-2 rounded-lg hover:bg-red-500/10 text-factorio-text-muted hover:text-red-400 transition-colors"
              title="删除"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
