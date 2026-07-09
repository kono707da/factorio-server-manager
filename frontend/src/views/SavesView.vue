<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import {
  Upload,
  Download,
  Trash2,
  ArrowRightLeft,
  Plus,
  RefreshCw,
  Save,
  Star,
} from 'lucide-vue-next'

interface SaveInfo {
  filename: string
  size: number
  modified: string
  is_active: boolean
}

const saves = ref<SaveInfo[]>([])
const uploading = ref(false)
const uploadProgress = ref(0)
const switchLoading = ref('')

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

async function fetchSaves() {
  try {
    const { data } = await api.get('/saves')
    saves.value = data.saves || []
  } catch { /* ignore */ }
}

async function uploadSave(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  const file = input.files[0]
  if (!file.name.endsWith('.zip')) {
    alert('只支持 .zip 格式的存档文件')
    return
  }
  uploading.value = true
  uploadProgress.value = 0
  try {
    const formData = new FormData()
    formData.append('file', file)
    await api.post('/saves/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) uploadProgress.value = Math.round((e.loaded / e.total) * 100)
      },
    })
    await fetchSaves()
    input.value = ''
  } catch (e: any) {
    alert(e.message || '上传失败')
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

function downloadSave(filename: string) {
  window.open(`/api/saves/download/${encodeURIComponent(filename)}`, '_blank')
}

async function deleteSave(filename: string) {
  if (!confirm(`确定要删除存档 ${filename} 吗？此操作不可恢复！`)) return
  try {
    await api.delete(`/saves/${encodeURIComponent(filename)}`)
    await fetchSaves()
  } catch (e: any) {
    alert(e.message || '删除失败')
  }
}

async function switchSave(filename: string) {
  if (!confirm(`切换存档到 ${filename}？如果服务器正在运行将自动重启。`)) return
  switchLoading.value = filename
  try {
    const { data } = await api.post('/saves/switch', { filename })
    if (data.success) alert(data.message || '切换成功')
    else alert(data.error || '切换失败')
    await fetchSaves()
  } catch (e: any) {
    alert(e.message || '切换失败')
  } finally {
    switchLoading.value = ''
  }
}

async function createSave() {
  const name = prompt('请输入新存档名称（不含 .zip 后缀）:')
  if (!name?.trim()) return
  try {
    const { data } = await api.post(`/saves/create?save_name=${encodeURIComponent(name.trim())}`)
    if (data.success) await fetchSaves()
    else alert(data.error || '创建失败')
  } catch (e: any) {
    alert(e.message || '创建失败')
  }
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  const files = event.dataTransfer?.files
  if (files?.length && files[0].name.endsWith('.zip')) {
    const dt = new DataTransfer()
    dt.items.add(files[0])
    const input = document.getElementById('save-upload') as HTMLInputElement
    if (input) {
      input.files = dt.files
      uploadSave({ target: input } as unknown as Event)
    }
  } else {
    alert('只支持 .zip 格式的存档文件')
  }
}

function handleDragOver(event: DragEvent) {
  event.preventDefault()
}

onMounted(fetchSaves)
</script>

<template>
  <div class="space-y-6">
    <!-- Upload Area -->
    <div
      class="card border-2 border-dashed border-factorio-border hover:border-factorio-accent transition-colors cursor-pointer"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @click="($refs.fileInput as HTMLInputElement)?.click()"
    >
      <input
        id="save-upload"
        ref="fileInput"
        type="file"
        accept=".zip"
        class="hidden"
        @change="uploadSave"
      />
      <div class="flex flex-col items-center py-6 text-factorio-text-muted">
        <Upload class="w-10 h-10 mb-3" />
        <p class="font-medium">点击或拖拽上传存档文件</p>
        <p class="text-sm mt-1">支持 .zip 格式</p>
        <div v-if="uploading" class="w-full max-w-xs mt-4">
          <div class="w-full h-2 bg-factorio-bg rounded-full overflow-hidden">
            <div class="h-full bg-factorio-accent rounded-full transition-all" :style="{ width: `${uploadProgress}%` }" />
          </div>
          <p class="text-center text-sm mt-1">{{ uploadProgress }}%</p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex gap-3">
      <button @click="fetchSaves" class="btn-ghost">
        <RefreshCw class="w-4 h-4" />
        刷新
      </button>
      <button @click="createSave" class="btn-primary">
        <Plus class="w-4 h-4" />
        新建存档
      </button>
    </div>

    <!-- Saves Table -->
    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-factorio-border bg-factorio-surface/50">
            <th class="text-left px-4 py-3 font-medium text-factorio-text-muted">文件名</th>
            <th class="text-left px-4 py-3 font-medium text-factorio-text-muted">大小</th>
            <th class="text-left px-4 py-3 font-medium text-factorio-text-muted">修改时间</th>
            <th class="text-left px-4 py-3 font-medium text-factorio-text-muted">状态</th>
            <th class="text-right px-4 py-3 font-medium text-factorio-text-muted">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="saves.length === 0">
            <td colspan="5" class="text-center py-10 text-factorio-text-muted">暂无存档文件</td>
          </tr>
          <tr
            v-for="save in saves"
            :key="save.filename"
            :class="[
              'border-b border-factorio-border/50 hover:bg-factorio-surface/30 transition-colors',
              save.is_active ? 'bg-factorio-accent/5' : ''
            ]"
          >
            <td class="px-4 py-3 font-mono text-xs">
              <div class="flex items-center gap-2">
                <Save class="w-4 h-4 text-factorio-text-muted shrink-0" />
                {{ save.filename }}
              </div>
            </td>
            <td class="px-4 py-3 text-factorio-text-muted">{{ formatSize(save.size) }}</td>
            <td class="px-4 py-3 text-factorio-text-muted">{{ formatDate(save.modified) }}</td>
            <td class="px-4 py-3">
              <span v-if="save.is_active" class="badge-success">
                <Star class="w-3 h-3 mr-1" />
                当前
              </span>
              <span v-else class="badge-info">可用</span>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center justify-end gap-2">
                <button
                  v-if="!save.is_active"
                  @click="switchSave(save.filename)"
                  :disabled="switchLoading === save.filename"
                  class="btn-ghost text-xs px-2 py-1"
                  title="切换为此存档"
                >
                  <ArrowRightLeft class="w-3.5 h-3.5" />
                  切换
                </button>
                <button @click="downloadSave(save.filename)" class="btn-ghost text-xs px-2 py-1" title="下载">
                  <Download class="w-3.5 h-3.5" />
                </button>
                <button
                  @click="deleteSave(save.filename)"
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
</template>
