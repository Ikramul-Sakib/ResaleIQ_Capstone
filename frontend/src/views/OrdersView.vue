<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { errorMessage, imageUrl } from '@/api'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import { useAuthStore } from '@/stores/auth'
import { formatPrice, timeAgo } from '@/utils'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const tab = computed(() => (route.query.tab === 'sales' ? 'sales' : 'purchases'))
const status = ref('')
const page = ref(1)
const data = ref({ items: [], page: 1, pages: 0, total: 0 })
const loading = ref(true)
const error = ref('')

const filters = [
  { key: '', label: 'All' },
  { key: 'active', label: 'Active' },
  { key: 'pending', label: 'Waiting' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'declined', label: 'Declined' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { role: tab.value === 'sales' ? 'seller' : 'buyer', status: status.value, page: page.value }
    data.value = (await api.get('/orders', { params })).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function nextStep(order) {
  if (tab.value === 'sales') {
    if (order.status === 'pending') return 'Accept or decline'
    if (order.status === 'accepted') return order.delivery_method === 'delivery' ? 'Ship the item' : 'Hand over the item'
    if (order.status === 'shipped') return 'Waiting for buyer to confirm'
  } else {
    if (order.status === 'pending') return 'Waiting for the seller'
    if (order.status === 'accepted') return order.payment_method === 'cod' ? 'Collect the item' : 'Pay and collect the item'
    if (order.status === 'shipped') return 'Confirm when received'
    if (order.status === 'completed' && !order.review) return 'Rate the seller'
  }
  return ''
}

watch([tab, status], () => {
  page.value = 1
  load()
}, { immediate: true })
</script>

<template>
  <div class="container page">
    <div class="page-header">
      <div>
        <h1>Orders</h1>
        <p>Track what you are buying and selling.</p>
      </div>
    </div>
    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'purchases' }" @click="router.replace({ query: { tab: 'purchases' } })">My purchases</button>
      <button class="tab" :class="{ active: tab === 'sales' }" @click="router.replace({ query: { tab: 'sales' } })">
        My sales <span v-if="auth.pendingSales" class="count">({{ auth.pendingSales }} waiting)</span>
      </button>
    </div>
    <div class="row mb">
      <button v-for="f in filters" :key="f.key" class="chip" :class="{ active: status === f.key }" @click="status = f.key">{{ f.label }}</button>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="!data.items.length" class="empty card">
      <h3>No orders here</h3>
      <p v-if="tab === 'purchases'">When you buy an item or make an offer, it shows up here.</p>
      <p v-else>Orders for your listings will appear here.</p>
      <RouterLink v-if="tab === 'purchases'" to="/" class="btn btn-primary">Browse items</RouterLink>
    </div>
    <div v-else class="list">
      <RouterLink v-for="order in data.items" :key="order.id" :to="`/orders/${order.id}`" class="card order">
        <img class="thumb big" :src="imageUrl(order.listing.image)" alt="" />
        <div class="min0 grow">
          <div class="row">
            <strong class="truncate">{{ order.listing.title }}</strong>
            <OrderStatusBadge :status="order.status" />
            <span v-if="order.is_offer" class="badge badge-ai">Offer</span>
          </div>
          <div class="tiny muted">
            #{{ order.id }} · {{ tab === 'sales' ? `Buyer: ${order.buyer?.name}` : `Seller: ${order.seller?.name}` }}
            · {{ order.payment_method_label }} · {{ order.delivery_method_label }} · {{ timeAgo(order.updated_at) }}
          </div>
          <div v-if="nextStep(order)" class="tiny next">Next: {{ nextStep(order) }}</div>
        </div>
        <div class="price-col">
          <span class="price">{{ formatPrice(order.price) }}</span>
          <span v-if="order.is_offer" class="tiny muted strike">{{ formatPrice(order.list_price) }}</span>
        </div>
      </RouterLink>
    </div>
    <PaginationBar :page="data.page" :pages="data.pages" @change="(p) => { page = p; load() }" />
  </div>
</template>

<style scoped>
.list { display: flex; flex-direction: column; gap: 10px; }
.order { display: flex; align-items: center; gap: 14px; padding: 12px 14px; color: var(--text); text-decoration: none !important; }
.order:hover { border-color: var(--primary); }
.thumb.big { width: 88px; height: 66px; }
.min0 { min-width: 0; }
.grow { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.next { color: #b45309; font-weight: 600; }
.price-col { display: flex; flex-direction: column; align-items: flex-end; flex-shrink: 0; }
.strike { text-decoration: line-through; }
</style>
