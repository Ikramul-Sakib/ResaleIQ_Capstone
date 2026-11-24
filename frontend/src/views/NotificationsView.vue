<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { errorMessage } from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { timeAgo } from '@/utils'

const router = useRouter()
const auth = useAuthStore()
const items = ref([])
const loading = ref(true)
const error = ref('')

const icons = { message: 'chat', listing_approved: 'check', listing_rejected: 'close', listing_removed: 'trash', report: 'flag', listing_pending: 'shield' }

async function load() {
  try {
    items.value = (await api.get('/notifications')).data.items
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function markAllRead() {
  await api.post('/notifications/read', {})
  items.value.forEach((item) => (item.is_read = true))
  auth.refreshSummary()
}

async function open(item) {
  if (!item.is_read) {
    api.post('/notifications/read', { ids: [item.id] }).then(() => auth.refreshSummary())
    item.is_read = true
  }
  if (item.link) router.push(item.link)
}

onMounted(load)
</script>

<template>
  <div class="container page medium">
    <div class="page-header">
      <h1>Notifications</h1>
      <button v-if="items.some((i) => !i.is_read)" class="btn btn-sm" @click="markAllRead">Mark all as read</button>
    </div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="!items.length" class="empty card">
      <h3>No notifications yet</h3>
      <p>You'll hear from us when your listings are reviewed or someone messages you.</p>
    </div>
    <div v-else class="card">
      <button v-for="item in items" :key="item.id" class="note" :class="{ unread: !item.is_read }" @click="open(item)">
        <span class="icon"><AppIcon :name="icons[item.type] || 'bell'" :size="18" /></span>
        <span class="text">
          <span>{{ item.message }}</span>
          <span class="tiny muted">{{ timeAgo(item.created_at) }}</span>
        </span>
        <span v-if="!item.is_read" class="dot" aria-label="Unread"></span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.note { display: flex; gap: 12px; align-items: center; width: 100%; padding: 14px 16px; border: none; border-bottom: 1px solid var(--border); background: none; font: inherit; text-align: left; cursor: pointer; color: var(--text); }
.note:last-child { border-bottom: none; }
.note:hover { background: #f7f9fa; }
.note.unread { background: #f3faf9; }
.icon { width: 36px; height: 36px; border-radius: 999px; background: var(--primary-soft); color: var(--primary-dark); display: grid; place-items: center; flex-shrink: 0; }
.text { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.dot { width: 9px; height: 9px; border-radius: 999px; background: var(--primary); flex-shrink: 0; }
</style>
