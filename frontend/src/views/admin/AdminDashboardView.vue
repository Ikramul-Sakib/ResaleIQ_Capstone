<script setup>
import { onMounted, ref } from 'vue'
import api, { errorMessage } from '@/api'
import AdminNav from '@/components/AdminNav.vue'
import { formatPrice, timeAgo } from '@/utils'

const stats = ref(null)
const error = ref('')

const actionLabels = {
  approve_listing: 'approved listing',
  reject_listing: 'rejected listing',
  remove_listing: 'removed listing',
  resolve_report: 'resolved report',
  dismiss_report: 'dismissed report',
  block_user: 'blocked user',
  unblock_user: 'unblocked user',
  create_category: 'created category',
  update_category: 'updated category',
  delete_category: 'deleted category',
  cancel_order: 'cancelled order',
}

onMounted(async () => {
  try {
    stats.value = (await api.get('/admin/stats')).data
  } catch (err) {
    error.value = errorMessage(err)
  }
})
</script>

<template>
  <div class="container page">
    <AdminNav />
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="!stats && !error" class="spinner"></div>
    <template v-if="stats">
      <div class="stats">
        <RouterLink to="/admin/listings" class="stat link">
          <div class="value warn">{{ stats.listings.pending }}</div><p class="label">Listings to review</p>
        </RouterLink>
        <RouterLink to="/admin/reports" class="stat link">
          <div class="value" :class="{ danger: stats.open_reports }">{{ stats.open_reports }}</div><p class="label">Open reports</p>
        </RouterLink>
        <div class="stat"><div class="value">{{ stats.listings.approved }}</div><p class="label">Live listings</p></div>
        <div class="stat"><div class="value">{{ stats.listings.sold }}</div><p class="label">Sold items</p></div>
        <RouterLink to="/admin/users" class="stat link">
          <div class="value">{{ stats.users }}</div><p class="label">Users ({{ stats.blocked_users }} blocked)</p>
        </RouterLink>
        <RouterLink to="/admin/orders" class="stat link">
          <div class="value">{{ stats.orders.pending + stats.orders.accepted + stats.orders.shipped }}</div><p class="label">Active orders</p>
        </RouterLink>
        <div class="stat"><div class="value">{{ stats.orders.completed }}</div><p class="label">Completed orders</p></div>
        <div class="stat"><div class="value">{{ formatPrice(stats.order_value) }}</div><p class="label">Value of completed orders</p></div>
      </div>

      <div class="card">
        <div class="card-body">
          <h2>Recent admin activity</h2>
          <p v-if="!stats.recent_actions.length" class="muted">No admin actions yet.</p>
          <ul v-else class="activity">
            <li v-for="action in stats.recent_actions" :key="action.id">
              <strong>{{ action.admin }}</strong> {{ actionLabels[action.action] || action.action }}
              <span v-if="action.note" class="muted">— {{ action.note }}</span>
              <span class="tiny muted when">{{ timeAgo(action.created_at) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.stat.link { color: var(--text); text-decoration: none; }
.stat.link:hover { border-color: var(--primary); }
.value.warn { color: #b45309; }
.value.danger { color: var(--danger); }
.activity { list-style: none; padding: 0; margin: 0; }
.activity li { padding: 10px 0; border-bottom: 1px solid var(--border); display: flex; gap: 6px; flex-wrap: wrap; align-items: baseline; }
.activity li:last-child { border-bottom: none; }
.when { margin-left: auto; }
</style>
