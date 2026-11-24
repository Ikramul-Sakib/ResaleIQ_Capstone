<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { errorMessage, fieldErrors, imageUrl } from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import CheckoutFields from '@/components/CheckoutFields.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { formatPrice } from '@/utils'

const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()

const cart = ref({ items: [], total: 0, available_count: 0 })
const loading = ref(true)
const placing = ref(false)
const errors = ref({})
const error = ref('')
const checkout = reactive({
  delivery_method: 'meetup',
  delivery_address: '',
  contact_phone: auth.user?.phone || '',
  payment_method: 'cod',
  note: '',
})

async function load() {
  try {
    cart.value = (await api.get('/cart')).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function remove(item) {
  try {
    await api.delete(`/cart/${item.id}`)
    auth.refreshSummary()
    load()
  } catch (err) {
    toast.error(errorMessage(err))
  }
}

async function placeOrders() {
  errors.value = {}
  error.value = ''
  placing.value = true
  try {
    const { data } = await api.post('/cart/checkout', checkout)
    const count = data.orders.length
    toast.show(`${count} order${count === 1 ? '' : 's'} placed. Sellers will confirm soon.`)
    if (data.skipped.length) toast.error(`${data.skipped.length} item(s) could not be ordered and stayed in your cart.`)
    auth.refreshSummary()
    router.push({ path: '/orders', query: { tab: 'purchases' } })
  } catch (err) {
    errors.value = fieldErrors(err)
    error.value = errorMessage(err)
  } finally {
    placing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container page">
    <div class="page-header">
      <div>
        <h1>Your cart</h1>
        <p>Each item is a separate order with its own seller.</p>
      </div>
    </div>
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="!cart.items.length" class="empty card">
      <AppIcon name="cart" :size="36" />
      <h3>Your cart is empty</h3>
      <p>Add items from any listing page.</p>
      <RouterLink to="/" class="btn btn-primary">Browse items</RouterLink>
    </div>
    <div v-else class="layout">
      <section class="card">
        <div v-for="item in cart.items" :key="item.id" class="line" :class="{ unavailable: !item.available }">
          <RouterLink :to="`/listings/${item.id}`" class="line-main">
            <img class="thumb big" :src="imageUrl(item.image)" alt="" />
            <div class="min0">
              <strong class="truncate">{{ item.title }}</strong>
              <div class="tiny muted">{{ item.condition_label }} · {{ item.location }}</div>
              <div v-if="!item.available" class="tiny problem">{{ item.problem }}</div>
            </div>
          </RouterLink>
          <span class="price">{{ formatPrice(item.price) }}</span>
          <button class="btn btn-ghost btn-sm" aria-label="Remove from cart" @click="remove(item)"><AppIcon name="trash" :size="16" /></button>
        </div>
      </section>

      <aside class="card card-body">
        <h2>Checkout</h2>
        <div class="row between total">
          <span>{{ cart.available_count }} item{{ cart.available_count === 1 ? '' : 's' }}</span>
          <strong class="price">{{ formatPrice(cart.total) }}</strong>
        </div>
        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <CheckoutFields v-model="checkout" :errors="errors" />
        <button class="btn btn-primary btn-block" :disabled="placing || !cart.available_count" @click="placeOrders">
          {{ placing ? 'Placing orders…' : `Place ${cart.available_count} order${cart.available_count === 1 ? '' : 's'}` }}
        </button>
        <p class="tiny muted mt" style="margin-bottom: 0">Nothing is charged now. Pay each seller by your chosen method after they accept.</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 20px; align-items: start; }
.line { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-bottom: 1px solid var(--border); }
.line:last-child { border-bottom: none; }
.line.unavailable { opacity: 0.6; }
.line-main { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; color: var(--text); text-decoration: none !important; }
.thumb.big { width: 88px; height: 66px; }
.min0 { min-width: 0; display: flex; flex-direction: column; }
.problem { color: var(--danger); }
.total { padding: 10px 0 14px; border-bottom: 1px solid var(--border); margin-bottom: 14px; font-size: 1.05rem; }
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
}
</style>
