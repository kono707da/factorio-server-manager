<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import {
  Download,
  Trash2,
  RotateCcw,
  Plus,
  RefreshCw,
  Clock,
  HardDrive,
  ToggleLeft,
  ToggleRight,
} from 'lucide-vue-next'

interface BackupRecord {
  id: number
  filename: string
  source_save: string
  file_size: number
  created_at: string
}

interface BackupConfig {
  enabled: boolean
  interval_hours: number
  max_backups: number
  last_backup_at: string | null
}

const backups = ref<BackupRecord[]>([])
const config = ref<BackupConfig>({ enabled: false, interval_hours: 6, max_backups: 10, last_backup_at: null })
const loading = ref({ trigger: false, config: false })

function formatSize(bytes: number) {
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${bytes} B`
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

async function fetchBackups() {
  try {
    const { data } = await api.get('/backups/list')
    backups.value = data.backups || []
  } catch { /* ignore */ }
}

async function fetchConfig() {
  try {
    const { data } = await api.get('/backups/config')
    config.value = data
  } catch { /* ignore */ }
}

async function updateConfig() {
  loading.value.config = true
  try {
    const { data } = await api.put('/backups/config', {
      enabled: config.value.enabled,
      interval_hours: config.value.interval_hours,
      max_backups: config.value.max_backups,
    })
    config.value = data
  } catch (e: any) {
    alert(e.message || '更新配置失败')
  } finally {
    loading.value.config = false
  }
}

async function toggleEnabled() {
  config.value.enabled = !config.value.enabled
  await updateConfig()
}

async function triggerBackup() {
  loading.value.trigger = true
  try {
    const { data } = await api.post('/backups/trigger')
    if (data.success) {
      alert('备份创建成功！')
      await fetchBackups()
      await fetchConfig()
    } else {
      alert(data.error || '备份失败')
    }
  } catch (e: any) {
    alert(e.message || '备份失败')
  } finally {
    loading.value.trigger = false
  }
}

function downloadBackup(filename: string) {
  window.open(`/api/backups/download/${encodeURIComponent(filename)}`, '_blank')
}

async function restoreBackup(filename: string) {
  if (!confirm(`确定要从备份 ${filename} 恢复吗？这将覆盖当前存档文件。`)) return
  try {
    const { data } = await api.post(`/backups/restore/${encodeURIComponent(filename)}`)
    if (data.success) alert(`恢复成功！已恢复到: ${data.restored_to}`)
    else alert(data.error || '恢复失败')
  } catch (e: any) {
    alert(e.message || '恢复失败')
  }
}

async function deleteBackup(filename: string) {
  if (!confirm(`确定要删除备份 ${filename} 吗？`)) return
  try {
    await api.delete(`/backups/${encodeURIComponent(filename)}`)
    await fetchBackups()
  } catch (e: any) {
    alert(e.message || '删除失败')
  }
}

onMounted(() => {
  fetchBackups()
  fetchConfig()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Config Card -->
    <div class="card">
      <h3 class="font-display font-semibold text-lg mb-4 flex items-center gap-2">
        <Clock class="w-5 h-5 text-factorio-accent" />
        备份计划
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label class="text-sm text-factorio-text-muted block mb-1">备份间隔（小时）</label>
          <input
            v-model.number="config.interval_hours"
            type="number"
            min="1"
            max="168"
            class="input w-full"
            @change="updateConfig"
          />
        </div>
        <div>
          <label class="text-sm text-factorio-text-muted block mb-1">最大保留备份数</label>
          <input
            v-model.number="config.max_backups"
            type="number"
            min="1"
            max="100"
            class="input w-full"
            @change="updateConfig"
          />
        </div>
        <div>
          <label class="text-sm text-factorio-text-muted block mb-1">上次备份</label>
          <p class="input bg-factorio-bg/50 cursor-default">
            {{ config.last_backup_at ? formatDate(config.last_backup_at) : '从未备份' }}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-4">
        <button @click="toggleEnabled" class="flex items-center gap-2">
          <component
            :is="config.enabled ? ToggleRight : ToggleLeft"
            :class="[
              'w-10 h-10 transition-colors',
              config.enabled ? 'text-factorio-success' : 'text-factorio-text-muted'
            ]"
          />
          <span class="text-sm">{{ config.enabled ? '已启用' : '已禁用' }}</span>
        </button>

        <div class="flex-1" />

        <button @click="triggerBackup" :disabled="loading.trigger" class="btn-primary">
          <Plus class="w-4 h-4" />
          {{ loading.trigger ? '备份中...' : '立即备份' }}
        </button>
      </div>
    </div>

    <!-- Backup List -->
    <div class="card">
      <h3 class="font-display font-semibold text-lg mb-4 flex items-center gap-2">
        <HardDrive class="w-5 h-5 text-factorio-accent" />
        备份列表
        <button @click="fetchBackups" class="btn-ghost ml-auto text-xs px-2 py-1">
          <RefreshCw class="w-3.5 h-3.5" />
          刷新
        </button>
      </h3>

      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-factorio-border bg-factorio-surface/50">
              <th class="text-left px-4 py-3 font-medium text-factorio-text-muted">备份文件</th>
              <th class="text-left px-4 py-3 font-medium text-factorio-text-muted">源存档</th>
              <th class="text-left px-4 py-3 font-medium text-factorio-text-muted">大小</th>
              <th class="text-left px-4 py-3 font-medium text-factorio-text-muted">创建时间</th>
              <th class="text-right px-4 py-3 font-medium text-factorio-text-muted">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="backups.length === 0">
              <td colspan="5" class="text-center py-10 text-factorio-text-muted">暂无备份记录</td>
            </tr>
            <tr
              v-for="b in backups"
              :key="b.id"
              class="border-b border-factorio-border/50 hover:bg-factorio-surface/30 transition-colors"
            >
              <td class="px-4 py-3 font-mono text-xs">{{ b.filename }}</td>
              <td class="px-4 py-3 text-factorio-text-muted">{{ b.source_save }}</td>
              <td class="px-4 py-3 text-factorio-text-muted">{{ formatSize(b.file_size) }}</td>
              <td class="px-4 py-3 text-factorio-text-muted">{{ formatDate(b.created_at) }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-2">
                  <button @click="downloadBackup(b.filename)" class="btn-ghost text-xs px-2 py-1" title="下载">
                    <Download class="w-3.5 h-3.5" />
                  </button>
                  <button @click="restoreBackup(b.filename)" class="btn-ghost text-xs px-2 py-1" title="恢复">
                    <RotateCcw class="w-3.5 h-3.5" />
                  </button>
                  <button
                    @click="deleteBackup(b.filename)"
                    class="btn-ghost text-xs px-2 py-1 text-factorio-danger hover:text-factorio-danger"
                    title="删除"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
