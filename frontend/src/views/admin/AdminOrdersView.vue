<script setup>
import { onMounted, ref, watch } from 'vue'
import api, { errorMessage } from '@/api'
import AdminNav from '@/components/AdminNav.vue'
import ModalDialog from '@/components/ModalDialog.vue'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import { useToastStore } from '@/stores/toast'
import { formatDate, formatPrice } from '@/utils'

const toast = useToastStore()
const status = ref('active')
const search = ref('')
const page = ref(1)
const data = ref({ items: [], page: 1, pages: 0, total: 0 })
const loading = ref(true)
const error = ref('')
const target = ref(null)
const reason = ref('')
const working = ref(false)

const filters = [
  { key: 'active', label: 'Active' },
  { key: 'pending', label: 'Waiting' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'declined', label: 'Declined' },
  { key: '', label: 'All' },
]

async function load() {
  loading.value = true
  try {
    data.value = (await api.get('/admin/orders', { params: { status: status.value, q: search.value, page: page.value } })).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function cancelOrder() {
  working.value = true
  try {
    await api.post(`/admin/orders/${target.value.id}/cancel`, { reason: reason.value })
    toast.show('Order cancelled. Buyer and seller were notified.')
    target.value = null
    load()
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    working.value = false
  }
}

watch(status, () => {
  page.value = 1
  load()
})
onMounted(load)
</script>

<template>
  <div class="container page">
    <AdminNav />
    <div class="row between mb">
      <div class="row">
        <button v-for="f in filters" :key="f.key" class="chip" :class="{ active: status === f.key }" @click="status = f.key">{{ f.label }}</button>
      </div>
      <form class="row" @submit.prevent="page = 1; load()">
        <input v-model="search" class="input" type="search" placeholder="Search item titles" style="width: 220px" />
        <button class="btn">Search</button>
      </form>
    </div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="!data.items.length" class="empty card"><h3>No orders</h3></div>
    <div v-else class="card table-wrap">
      <table class="table">
        <thead>
          <tr><th>#</th><th>Item</th><th>Buyer</th><th>Seller</th><th>Price</th><th>Payment</th><th>Status</th><th>Updated</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="order in data.items" :key="order.id">
            <td>{{ order.id }}</td>
            <td class="title-cell">
              <RouterLink v-if="order.listing.status !== 'deleted'" :to="`/listings/${order.listing.id}`">{{ order.listing.title }}</RouterLink>
              <span v-else>{{ order.listing.title }}</span>
              <span v-if="order.is_offer" class="badge badge-ai">Offer</span>
            </td>
            <td>{{ order.buyer?.name }}</td>
            <td>{{ order.seller?.name }}</td>
            <td class="price">{{ formatPrice(order.price) }}</td>
            <td>{{ order.payment_method_label }}<br /><span class="tiny muted">{{ order.payment_status }}</span></td>
            <td><OrderStatusBadge :status="order.status" /></td>
            <td class="tiny">{{ formatDate(order.updated_at) }}</td>
            <td>
              <button v-if="['pending', 'accepted', 'shipped'].includes(order.status)" class="btn btn-sm btn-ghost" @click="target = order; reason = ''">Cancel</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :page="data.page" :pages="data.pages" @change="(p) => { page = p; load() }" />

    <ModalDialog v-if="target" title="Cancel order" @close="target = null">
      <p class="small muted">#{{ target.id }} · {{ target.listing.title }}</p>
      <div class="form-group">
        <label for="ao-reason">Reason (sent to buyer and seller)</label>
        <textarea id="ao-reason" v-model="reason" class="input" rows="3" maxlength="500"></textarea>
      </div>
      <template #footer>
        <button class="btn" @click="target = null">Back</button>
        <button class="btn btn-danger" :disabled="working || reason.trim().length < 5" @click="cancelOrder">Cancel order</button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.title-cell { max-width: 260px; }
</style>
