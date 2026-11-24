<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { errorMessage, imageUrl } from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import ModalDialog from '@/components/ModalDialog.vue'
import OrderDialog from '@/components/OrderDialog.vue'
import StarRating from '@/components/StarRating.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { REPORT_REASONS, formatDate, formatPrice, timeAgo } from '@/utils'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

const listing = ref(null)
const loading = ref(true)
const error = ref('')
const activeImage = ref(0)
const message = ref('')
const sending = ref(false)

const showReport = ref(false)
const report = ref({ reason: 'fraud', details: '' })
const showSold = ref(false)
const soldPrice = ref('')
const showDelete = ref(false)
const working = ref(false)
const orderMode = ref('') // '' | 'buy' | 'offer'
const cartBusy = ref(false)

const images = computed(() => listing.value?.images || [])
const canContact = computed(() => listing.value && !listing.value.is_owner && ['approved', 'reserved'].includes(listing.value.status))
const canBuy = computed(() => listing.value && !listing.value.is_owner && listing.value.status === 'approved' && !listing.value.active_order_id)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/listings/${route.params.id}`)
    listing.value = data
    message.value = `Hi, is "${data.title}" still available?`
    soldPrice.value = data.price
  } catch (err) {
    error.value = err.response?.status === 404 ? 'This listing does not exist or is no longer available.' : errorMessage(err)
  } finally {
    loading.value = false
  }
}

function requireLogin() {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}

async function sendMessage() {
  if (!auth.isLoggedIn) return requireLogin()
  if (!message.value.trim()) return
  sending.value = true
  try {
    const { data } = await api.post('/conversations', { listing_id: listing.value.id, body: message.value })
    router.push(`/messages/${data.id}`)
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    sending.value = false
  }
}

async function toggleWishlist() {
  if (!auth.isLoggedIn) return requireLogin()
  try {
    if (listing.value.in_wishlist) await api.delete(`/wishlist/${listing.value.id}`)
    else await api.post(`/wishlist/${listing.value.id}`)
    listing.value.in_wishlist = !listing.value.in_wishlist
    toast.show(listing.value.in_wishlist ? 'Saved to your wishlist.' : 'Removed from your wishlist.')
  } catch (err) {
    toast.error(errorMessage(err))
  }
}

function startOrder(mode) {
  if (!auth.isLoggedIn) return requireLogin()
  orderMode.value = mode
}

async function toggleCart() {
  if (!auth.isLoggedIn) return requireLogin()
  if (listing.value.in_cart) return router.push('/cart')
  cartBusy.value = true
  try {
    await api.post(`/cart/${listing.value.id}`)
    listing.value.in_cart = true
    auth.refreshSummary()
    toast.show('Added to your cart.')
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    cartBusy.value = false
  }
}

async function submitReport() {
  working.value = true
  try {
    const { data } = await api.post(`/listings/${listing.value.id}/report`, report.value)
    toast.show(data.message)
    showReport.value = false
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    working.value = false
  }
}

async function markSold() {
  working.value = true
  try {
    const { data } = await api.post(`/listings/${listing.value.id}/sold`, { sold_price: soldPrice.value })
    listing.value = { ...listing.value, ...data }
    showSold.value = false
    toast.show('Marked as sold. Congratulations!')
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    working.value = false
  }
}

async function deleteListing() {
  working.value = true
  try {
    await api.delete(`/listings/${listing.value.id}`)
    toast.show('Listing deleted.')
    router.push('/dashboard')
  } catch (err) {
    toast.error(errorMessage(err))
    working.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container page">
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="error" class="empty card">
      <h3>Listing unavailable</h3>
      <p>{{ error }}</p>
      <RouterLink to="/" class="btn btn-primary">Browse other items</RouterLink>
    </div>

    <template v-else-if="listing">
      <div v-if="listing.is_owner && listing.status !== 'approved'" class="alert" :class="listing.status === 'rejected' || listing.status === 'removed' ? 'alert-error' : listing.status === 'sold' ? 'alert-info' : 'alert-warning'">
        <template v-if="listing.status === 'pending'">This listing is waiting for admin review. Only you can see it until it is approved.</template>
        <template v-else-if="listing.status === 'rejected'">Not approved: {{ listing.rejection_reason }} Edit the listing to submit it again.</template>
        <template v-else-if="listing.status === 'removed'">Removed by an administrator: {{ listing.rejection_reason }}</template>
        <template v-else-if="listing.status === 'sold'">You sold this item for {{ formatPrice(listing.sold_price) }}.</template>
        <template v-else-if="listing.status === 'reserved'">
          This item is reserved for a buyer.
          <RouterLink v-if="listing.active_order_id" :to="`/orders/${listing.active_order_id}`">View the order</RouterLink>
        </template>
      </div>
      <div v-if="listing.is_owner && listing.pending_order_count" class="alert alert-info">
        You have {{ listing.pending_order_count }} order{{ listing.pending_order_count === 1 ? '' : 's' }} waiting for this item.
        <RouterLink :to="{ path: '/orders', query: { tab: 'sales' } }">Review orders</RouterLink>
      </div>

      <div class="detail">
        <section class="gallery card">
          <div class="main-image">
            <img v-if="images.length" :src="imageUrl(images[activeImage]?.url)" :alt="listing.title" />
            <span v-if="listing.status === 'sold'" class="sold-tag">SOLD</span>
            <span v-else-if="listing.status === 'reserved'" class="sold-tag reserved">RESERVED</span>
          </div>
          <div v-if="images.length > 1" class="thumbs">
            <button
              v-for="(image, index) in images"
              :key="image.id"
              :class="{ active: index === activeImage }"
              :aria-label="`Photo ${index + 1}`"
              @click="activeImage = index"
            >
              <img :src="imageUrl(image.url)" alt="" />
            </button>
          </div>
        </section>

        <section class="info">
          <div class="card card-body">
            <div class="row between">
              <span class="badge">{{ listing.category?.name }}</span>
              <StatusBadge v-if="listing.is_owner || listing.status !== 'approved'" :status="listing.status" />
            </div>
            <h1 class="mt">{{ listing.title }}</h1>
            <div class="big-price price">{{ formatPrice(listing.price) }}</div>
            <div class="facts">
              <div><span class="muted">Condition</span><strong>{{ listing.condition_label }}</strong></div>
              <div v-if="listing.brand"><span class="muted">Brand</span><strong>{{ listing.brand }}</strong></div>
              <div v-if="listing.model"><span class="muted">Model</span><strong>{{ listing.model }}</strong></div>
              <div><span class="muted">Location</span><strong>{{ listing.location }}</strong></div>
              <div><span class="muted">Posted</span><strong>{{ timeAgo(listing.approved_at || listing.created_at) }}</strong></div>
              <div><span class="muted">Views</span><strong>{{ listing.views }}</strong></div>
            </div>

            <div v-if="listing.is_owner" class="row mt">
              <RouterLink v-if="['pending', 'approved', 'rejected'].includes(listing.status) && !listing.pending_order_count" :to="`/listings/${listing.id}/edit`" class="btn btn-primary">
                <AppIcon name="edit" :size="16" /> Edit
              </RouterLink>
              <button v-if="listing.status === 'approved'" class="btn" @click="showSold = true"><AppIcon name="check" :size="16" /> Sold elsewhere</button>
              <button v-if="listing.status !== 'reserved'" class="btn btn-ghost" @click="showDelete = true"><AppIcon name="trash" :size="16" /> Delete</button>
            </div>
            <template v-else>
              <div v-if="listing.active_order_id" class="buy-box">
                <p class="small" style="margin: 0">You have an active order for this item.</p>
                <RouterLink :to="`/orders/${listing.active_order_id}`" class="btn btn-primary btn-block mt"><AppIcon name="receipt" :size="16" /> View your order</RouterLink>
              </div>
              <div v-else-if="canBuy" class="buy-box">
                <button class="btn btn-primary btn-block" @click="startOrder('buy')">Buy now · {{ formatPrice(listing.price) }}</button>
                <div class="row mt buy-row">
                  <button class="btn" @click="startOrder('offer')"><AppIcon name="tag" :size="16" /> Make an offer</button>
                  <button class="btn" :disabled="cartBusy" @click="toggleCart">
                    <AppIcon name="cart" :size="16" /> {{ listing.in_cart ? 'In cart' : 'Add to cart' }}
                  </button>
                </div>
              </div>
              <div v-else-if="listing.status === 'reserved'" class="alert alert-warning mt" style="margin-bottom: 0">This item is reserved for another buyer.</div>
            </template>
            <div v-if="!listing.is_owner" class="row mt">
              <button class="btn" :class="{ saved: listing.in_wishlist }" @click="toggleWishlist">
                <AppIcon name="heart" :size="16" :filled="listing.in_wishlist" />
                {{ listing.in_wishlist ? 'Saved' : 'Save' }}
              </button>
              <button v-if="listing.status === 'approved'" class="btn btn-ghost" @click="auth.isLoggedIn ? (showReport = true) : requireLogin()">
                <AppIcon name="flag" :size="16" /> Report
              </button>
            </div>
          </div>

          <div class="card card-body mt">
            <h3>Seller</h3>
            <RouterLink :to="`/sellers/${listing.seller.id}`" class="seller">
              <span class="avatar">{{ listing.seller.name.charAt(0).toUpperCase() }}</span>
              <span>
                <strong>{{ listing.seller.name }}</strong>
                <span v-if="listing.seller_stats.rating_count" class="d-block small">
                  <StarRating :model-value="listing.seller_stats.rating_avg" :size="14" />
                  {{ listing.seller_stats.rating_avg }} ({{ listing.seller_stats.rating_count }} review{{ listing.seller_stats.rating_count === 1 ? '' : 's' }})
                </span>
                <span class="tiny muted d-block">Member since {{ formatDate(listing.seller.member_since) }} · {{ listing.seller_stats.active_listings }} active · {{ listing.seller_stats.sold_listings }} sold</span>
              </span>
            </RouterLink>

            <template v-if="canContact">
              <RouterLink v-if="listing.conversation_id" :to="`/messages/${listing.conversation_id}`" class="btn btn-primary btn-block mt">
                <AppIcon name="chat" :size="16" /> Open your conversation
              </RouterLink>
              <form v-else class="mt" @submit.prevent="sendMessage">
                <label for="msg" class="label">Message the seller</label>
                <textarea id="msg" v-model="message" class="input" rows="3" maxlength="2000"></textarea>
                <button class="btn btn-primary btn-block mt" :disabled="sending">
                  <AppIcon name="send" :size="16" /> {{ auth.isLoggedIn ? (sending ? 'Sending…' : 'Send message') : 'Log in to contact seller' }}
                </button>
              </form>
            </template>
          </div>
        </section>
      </div>

      <section class="card card-body mt description">
        <h2>Description</h2>
        <p>{{ listing.description }}</p>
      </section>
    </template>

    <OrderDialog v-if="orderMode" :listing="listing" :mode="orderMode" @close="orderMode = ''" />

    <ModalDialog v-if="showReport" title="Report this listing" @close="showReport = false">
      <div class="form-group">
        <label for="r-reason">Reason</label>
        <select id="r-reason" v-model="report.reason" class="input">
          <option v-for="r in REPORT_REASONS" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </div>
      <div class="form-group">
        <label for="r-details">Details (optional)</label>
        <textarea id="r-details" v-model="report.details" class="input" maxlength="1000" placeholder="What is wrong with this listing?"></textarea>
      </div>
      <template #footer>
        <button class="btn" @click="showReport = false">Cancel</button>
        <button class="btn btn-danger" :disabled="working" @click="submitReport">Send report</button>
      </template>
    </ModalDialog>

    <ModalDialog v-if="showSold" title="Mark as sold" @close="showSold = false">
      <div class="form-group">
        <label for="sold-price">Final sale price (৳)</label>
        <input id="sold-price" v-model="soldPrice" class="input" type="number" min="0" />
        <p class="hint">This helps improve price estimates. It is only shown to you.</p>
      </div>
      <template #footer>
        <button class="btn" @click="showSold = false">Cancel</button>
        <button class="btn btn-primary" :disabled="working" @click="markSold">Mark as sold</button>
      </template>
    </ModalDialog>

    <ModalDialog v-if="showDelete" title="Delete listing?" @close="showDelete = false">
      <p>This permanently deletes the listing, its photos and its conversations.</p>
      <template #footer>
        <button class="btn" @click="showDelete = false">Cancel</button>
        <button class="btn btn-danger" :disabled="working" @click="deleteListing">Delete</button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.detail { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(300px, 1fr); gap: 20px; align-items: start; }
.gallery { overflow: hidden; }
.main-image { aspect-ratio: 4 / 3; background: #e9edf1; position: relative; }
.main-image img { width: 100%; height: 100%; object-fit: contain; background: #111827; }
.sold-tag { position: absolute; left: 14px; top: 14px; background: #1e40af; color: #fff; font-weight: 700; padding: 4px 10px; border-radius: 6px; }
.sold-tag.reserved { background: #b45309; }
.buy-box { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); }
.buy-row > .btn { flex: 1; }
.thumbs { display: flex; gap: 8px; padding: 10px; overflow-x: auto; }
.thumbs button { border: 2px solid transparent; padding: 0; border-radius: 8px; overflow: hidden; cursor: pointer; flex-shrink: 0; background: none; }
.thumbs button.active { border-color: var(--primary); }
.thumbs img { width: 72px; height: 54px; object-fit: cover; }
.big-price { font-size: 1.7rem; margin-bottom: 12px; }
.facts { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; border-top: 1px solid var(--border); padding-top: 12px; }
.facts div { display: flex; flex-direction: column; font-size: 0.92rem; }
.facts .muted { font-size: 0.8rem; }
.seller { display: flex; align-items: center; gap: 12px; color: var(--text); }
.avatar { width: 44px; height: 44px; border-radius: 999px; background: var(--primary-soft); color: var(--primary-dark); display: grid; place-items: center; font-weight: 700; font-size: 1.1rem; flex-shrink: 0; }
.d-block { display: block; }
.btn.saved { color: var(--danger); border-color: #f5c2c2; }
.description p { white-space: pre-line; }
@media (max-width: 860px) {
  .detail { grid-template-columns: 1fr; }
}
</style>
