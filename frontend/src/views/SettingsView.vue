<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { Save, Settings, CheckCircle } from 'lucide-vue-next'

interface AppConfig {
  id: number
  factorio_dir: string
  saves_dir: string
  backups_dir: string
  logs_dir: string
  server_port: number
  game_password: string
  max_players: number
  require_user_verification: boolean
  autosave_interval: number
  autosave_slots: number
}

const config = ref<AppConfig>({
  id: 1,
  factorio_dir: '',
  saves_dir: '',
  backups_dir: '',
  logs_dir: '',
  server_port: 34197,
  game_password: '',
  max_players: 10,
  require_user_verification: true,
  autosave_interval: 5,
  autosave_slots: 5,
})
const saving = ref(false)
const saved = ref(false)

async function fetchConfig() {
  try {
    const { data } = await api.get('/config')
    config.value = data
  } catch { /* ignore */ }
}

async function saveConfig() {
  saving.value = true
  saved.value = false
  try {
    const { data } = await api.put('/config', config.value)
    config.value = data
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch (e: any) {
    alert(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(fetchConfig)
</script>

<template>
  <div class="space-y-6">
    <div class="card">
      <h3 class="font-display font-semibold text-lg mb-4 flex items-center gap-2">
        <Settings class="w-5 h-5 text-factorio-accent" />
        服务器配置
      </h3>

      <div class="space-y-6">
        <!-- Paths -->
        <div>
          <h4 class="text-sm font-medium text-factorio-text-muted uppercase tracking-wider mb-3">路径配置</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">Factorio 安装目录</label>
              <input v-model="config.factorio_dir" class="input w-full" placeholder="/opt/factorio" />
            </div>
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">存档目录</label>
              <input v-model="config.saves_dir" class="input w-full" placeholder="/opt/factorio/saves" />
            </div>
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">备份目录</label>
              <input v-model="config.backups_dir" class="input w-full" placeholder="/opt/factorio/backups" />
            </div>
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">日志目录</label>
              <input v-model="config.logs_dir" class="input w-full" placeholder="/opt/factorio/logs" />
            </div>
          </div>
        </div>

        <!-- Game Settings -->
        <div>
          <h4 class="text-sm font-medium text-factorio-text-muted uppercase tracking-wider mb-3">游戏设置</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">服务器端口</label>
              <input v-model.number="config.server_port" type="number" class="input w-full" min="1" max="65535" />
            </div>
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">游戏密码（留空则无密码）</label>
              <input v-model="config.game_password" type="password" class="input w-full" placeholder="留空则无密码" />
            </div>
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">最大玩家数</label>
              <input v-model.number="config.max_players" type="number" class="input w-full" min="1" max="255" />
            </div>
            <div class="flex items-center gap-3 pt-5">
              <input
                v-model="config.require_user_verification"
                type="checkbox"
                id="verify"
                class="rounded bg-factorio-bg border-factorio-border"
              />
              <label for="verify" class="text-sm cursor-pointer">要求玩家验证（需要 Factorio 账号）</label>
            </div>
          </div>
        </div>

        <!-- Autosave -->
        <div>
          <h4 class="text-sm font-medium text-factorio-text-muted uppercase tracking-wider mb-3">自动保存</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">自动保存间隔（分钟）</label>
              <input v-model.number="config.autosave_interval" type="number" class="input w-full" min="1" max="120" />
            </div>
            <div>
              <label class="text-sm text-factorio-text-muted block mb-1">自动保存份数</label>
              <input v-model.number="config.autosave_slots" type="number" class="input w-full" min="1" max="20" />
            </div>
          </div>
        </div>

        <!-- Save Button -->
        <div class="flex items-center gap-3 pt-2">
          <button @click="saveConfig" :disabled="saving" class="btn-primary">
            <Save class="w-4 h-4" />
            {{ saving ? '保存中...' : '保存配置' }}
          </button>
          <transition name="fade">
            <span v-if="saved" class="flex items-center gap-1 text-factorio-success text-sm">
              <CheckCircle class="w-4 h-4" />
              已保存
            </span>
          </transition>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
