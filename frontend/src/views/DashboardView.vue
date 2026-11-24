<script setup>
import { computed, onMounted, ref } from 'vue'
import api, { errorMessage, imageUrl } from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import ModalDialog from '@/components/ModalDialog.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { formatPrice, timeAgo } from '@/utils'

const toast = useToastStore()
const auth = useAuthStore()
const items = ref([])
const stats = ref({})
const loading = ref(true)
const error = ref('')
const tab = ref('all')
const soldTarget = ref(null)
const soldPrice = ref('')
const deleteTarget = ref(null)
const working = ref(false)

const tabs = [
  { key: 'all', label: 'All' },
  { key: 'approved', label: 'Live' },
  { key: 'reserved', label: 'Reserved' },
  { key: 'pending', label: 'Pending' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'sold', label: 'Sold' },
  { key: 'removed', label: 'Removed' },
]

const visible = computed(() => (tab.value === 'all' ? items.value : items.value.filter((i) => i.status === tab.value)))

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/listings/mine')
    items.value = data.items
    stats.value = data.stats
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function openSold(item) {
  soldTarget.value = item
  soldPrice.value = item.price
}

async function confirmSold() {
  working.value = true
  try {
    await api.post(`/listings/${soldTarget.value.id}/sold`, { sold_price: soldPrice.value })
    toast.show('Marked as sold.')
    soldTarget.value = null
    await load()
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    working.value = false
  }
}

async function confirmDelete() {
  working.value = true
  try {
    await api.delete(`/listings/${deleteTarget.value.id}`)
    toast.show('Listing deleted.')
    deleteTarget.value = null
    await load()
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    working.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container page">
    <div class="page-header">
      <div>
        <h1>My listings</h1>
        <p>Track approval, edit your ads and record sales.</p>
      </div>
      <RouterLink to="/sell" class="btn btn-accent"><AppIcon name="plus" :size="18" /> New listing</RouterLink>
    </div>

    <div v-if="auth.pendingSales" class="alert alert-warning row between">
      <span>You have {{ auth.pendingSales }} order{{ auth.pendingSales === 1 ? '' : 's' }} waiting for your answer.</span>
      <RouterLink :to="{ path: '/orders', query: { tab: 'sales' } }" class="btn btn-sm">Review orders</RouterLink>
    </div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="spinner"></div>
    <template v-else>
      <div class="stats">
        <div class="stat"><div class="value">{{ stats.approved || 0 }}</div><p class="label">Live listings</p></div>
        <div class="stat"><div class="value">{{ stats.pending || 0 }}</div><p class="label">Waiting for review</p></div>
        <div class="stat"><div class="value">{{ stats.sold || 0 }}</div><p class="label">Sold</p></div>
        <div class="stat"><div class="value">{{ stats.total_views || 0 }}</div><p class="label">Total views</p></div>
        <div class="stat"><div class="value">{{ formatPrice(stats.sales_value || 0) }}</div><p class="label">Sales value</p></div>
      </div>

      <div class="tabs">
        <button v-for="t in tabs" :key="t.key" class="tab" :class="{ active: tab === t.key }" @click="tab = t.key">
          {{ t.label }}<span class="count">{{ t.key === 'all' ? stats.total : stats[t.key] || 0 }}</span>
        </button>
      </div>

      <div v-if="!visible.length" class="empty card">
        <h3>No listings here</h3>
        <p v-if="!items.length">Post your first item. It only takes a minute.</p>
        <RouterLink v-if="!items.length" to="/sell" class="btn btn-primary">Sell an item</RouterLink>
      </div>
      <div v-else class="list">
        <div v-for="item in visible" :key="item.id" class="item card">
          <RouterLink :to="`/listings/${item.id}`" class="item-main">
            <img class="thumb big" :src="imageUrl(item.image)" alt="" />
            <div class="item-text">
              <div class="row">
                <strong class="truncate">{{ item.title }}</strong>
                <StatusBadge :status="item.status" />
              </div>
              <div class="price">{{ formatPrice(item.status === 'sold' ? item.sold_price : item.price) }}</div>
              <div class="tiny muted">{{ item.views }} views · updated {{ timeAgo(item.updated_at) }}</div>
              <div v-if="item.rejection_reason && ['rejected', 'removed'].includes(item.status)" class="tiny reason">
                Reason: {{ item.rejection_reason }}
              </div>
            </div>
          </RouterLink>
          <div class="item-actions">
            <RouterLink v-if="['pending', 'approved', 'rejected'].includes(item.status)" :to="`/listings/${item.id}/edit`" class="btn btn-sm">
              <AppIcon name="edit" :size="15" /> Edit
            </RouterLink>
            <button v-if="item.status === 'approved'" class="btn btn-sm" @click="openSold(item)"><AppIcon name="check" :size="15" /> Sold</button>
            <button v-if="item.status !== 'reserved'" class="btn btn-sm btn-ghost" aria-label="Delete" @click="deleteTarget = item"><AppIcon name="trash" :size="15" /></button>
          </div>
        </div>
      </div>
    </template>

    <ModalDialog v-if="soldTarget" title="Mark as sold" @close="soldTarget = null">
      <p class="small muted">{{ soldTarget.title }}</p>
      <div class="form-group">
        <label for="d-sold">Final sale price (৳)</label>
        <input id="d-sold" v-model="soldPrice" class="input" type="number" min="0" />
      </div>
      <template #footer>
        <button class="btn" @click="soldTarget = null">Cancel</button>
        <button class="btn btn-primary" :disabled="working" @click="confirmSold">Mark as sold</button>
      </template>
    </ModalDialog>

    <ModalDialog v-if="deleteTarget" title="Delete listing?" @close="deleteTarget = null">
      <p>“{{ deleteTarget.title }}” and its photos and conversations will be permanently deleted.</p>
      <template #footer>
        <button class="btn" @click="deleteTarget = null">Cancel</button>
        <button class="btn btn-danger" :disabled="working" @click="confirmDelete">Delete</button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.list { display: flex; flex-direction: column; gap: 10px; }
.item { display: flex; align-items: center; gap: 12px; padding: 12px; }
.item-main { display: flex; gap: 14px; align-items: center; flex: 1; min-width: 0; color: var(--text); text-decoration: none !important; }
.thumb.big { width: 96px; height: 72px; }
.item-text { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.item-actions { display: flex; gap: 6px; flex-shrink: 0; }
.reason { color: var(--danger); }
@media (max-width: 640px) {
  .item { flex-direction: column; align-items: stretch; }
  .item-actions { justify-content: flex-end; }
}
</style>
