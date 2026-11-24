<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api, { errorMessage, imageUrl } from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import ModalDialog from '@/components/ModalDialog.vue'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import StarRating from '@/components/StarRating.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { formatDate, formatPrice, timeAgo } from '@/utils'

const route = useRoute()
const auth = useAuthStore()
const toast = useToastStore()

const order = ref(null)
const loading = ref(true)
const error = ref('')
const working = ref(false)
const dialog = ref('') // decline | cancel
const reason = ref('')
const trx = ref('')
const rating = ref(5)
const comment = ref('')

const isSeller = computed(() => order.value?.role === 'seller')
const isBuyer = computed(() => order.value?.role === 'buyer')
const mobilePay = computed(() => order.value && order.value.payment_method !== 'cod')
const handOverWord = computed(() => (order.value?.delivery_method === 'delivery' ? 'Shipped' : 'Handed over'))

const steps = computed(() => {
  if (!order.value) return []
  const o = order.value
  return [
    { label: o.is_offer ? 'Offer sent' : 'Order placed', at: o.created_at },
    { label: 'Accepted by seller', at: o.accepted_at },
    { label: handOverWord.value, at: o.shipped_at },
    { label: 'Received · completed', at: o.completed_at },
  ]
})
const closed = computed(() => ['declined', 'cancelled'].includes(order.value?.status))

async function load() {
  try {
    order.value = (await api.get(`/orders/${route.params.id}`)).data
  } catch (err) {
    error.value = err.response?.status === 404 ? 'This order was not found.' : errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function act(action, body = {}, message = 'Order updated.') {
  working.value = true
  try {
    order.value = (await api.post(`/orders/${order.value.id}/${action}`, body)).data
    toast.show(message)
    dialog.value = ''
    auth.refreshSummary()
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    working.value = false
  }
}

function openDialog(kind) {
  dialog.value = kind
  reason.value = ''
}

onMounted(load)
</script>

<template>
  <div class="container page">
    <RouterLink :to="{ path: '/orders', query: { tab: isSeller ? 'sales' : 'purchases' } }" class="small back">
      <AppIcon name="arrowLeft" :size="16" /> All orders
    </RouterLink>
    <div v-if="loading" class="spinner"></div>
    <div v-else-if="error" class="empty card"><h3>{{ error }}</h3></div>

    <template v-else-if="order">
      <div class="page-header">
        <div>
          <h1>Order #{{ order.id }}</h1>
          <p>{{ isSeller ? `Buyer: ${order.buyer?.name}` : `Seller: ${order.seller?.name}` }} · placed {{ timeAgo(order.created_at) }}</p>
        </div>
        <OrderStatusBadge :status="order.status" />
      </div>

      <div class="layout">
        <div>
          <section class="card card-body item">
            <img class="thumb huge" :src="imageUrl(order.listing.image)" alt="" />
            <div class="grow">
              <RouterLink v-if="order.listing.status !== 'deleted'" :to="`/listings/${order.listing.id}`" class="bold">{{ order.listing.title }}</RouterLink>
              <strong v-else>{{ order.listing.title }} <span class="muted tiny">(listing deleted)</span></strong>
              <div class="price big">{{ formatPrice(order.price) }}</div>
              <div v-if="order.is_offer" class="tiny muted">Offer · asking price was {{ formatPrice(order.list_price) }}</div>
            </div>
          </section>

          <section class="card card-body mt">
            <h2>Progress</h2>
            <div v-if="closed" class="alert alert-error">
              {{ order.status === 'declined' ? 'The seller declined this order.' : `Cancelled by the ${order.cancelled_by}.` }}
              <span v-if="order.status_note"> Reason: {{ order.status_note }}</span>
            </div>
            <ol v-else class="steps">
              <li v-for="(step, index) in steps" :key="index" :class="{ done: step.at }">
                <span class="mark"><AppIcon v-if="step.at" name="check" :size="14" /></span>
                <span>{{ step.label }}</span>
                <span class="tiny muted">{{ step.at ? formatDate(step.at) : '' }}</span>
              </li>
            </ol>

            <!-- Actions for the current step -->
            <div class="actions">
              <template v-if="isSeller && order.status === 'pending'">
                <p class="small">Accepting reserves the item for this buyer and declines any other waiting orders.</p>
                <div class="row">
                  <button class="btn btn-primary" :disabled="working" @click="act('accept', {}, 'Order accepted. The item is now reserved.')">Accept {{ order.is_offer ? 'offer' : 'order' }}</button>
                  <button class="btn" :disabled="working" @click="openDialog('decline')">Decline</button>
                </div>
              </template>
              <template v-if="isSeller && order.status === 'accepted'">
                <div class="row">
                  <button class="btn btn-primary" :disabled="working" @click="act('ship', {}, 'Buyer notified.')">
                    <AppIcon name="package" :size="16" /> Mark as {{ handOverWord.toLowerCase() }}
                  </button>
                  <button class="btn btn-ghost" :disabled="working" @click="openDialog('cancel')">Cancel order</button>
                </div>
              </template>
              <template v-if="isSeller && order.status === 'shipped'">
                <p class="small muted">Waiting for the buyer to confirm they received the item.</p>
              </template>

              <template v-if="isBuyer && order.status === 'pending'">
                <p class="small muted">Waiting for the seller to respond.</p>
                <button class="btn btn-ghost" :disabled="working" @click="openDialog('cancel')">Cancel {{ order.is_offer ? 'offer' : 'order' }}</button>
              </template>
              <template v-if="isBuyer && ['accepted', 'shipped'].includes(order.status)">
                <div class="row">
                  <button class="btn btn-primary" :disabled="working" @click="act('complete', {}, 'Thanks! The sale is complete.')">
                    <AppIcon name="check" :size="16" /> I received the item
                  </button>
                  <button v-if="order.status === 'accepted'" class="btn btn-ghost" :disabled="working" @click="openDialog('cancel')">Cancel order</button>
                </div>
                <p class="tiny muted mt" style="margin-bottom: 0">Only confirm after you have the item and checked it.</p>
              </template>
            </div>
          </section>

          <section v-if="order.status === 'completed'" class="card card-body mt">
            <h2>Review</h2>
            <div v-if="order.review">
              <StarRating :model-value="order.review.rating" />
              <p v-if="order.review.comment" class="mt">“{{ order.review.comment }}”</p>
              <p class="tiny muted">{{ isBuyer ? 'Your review' : `Review by ${order.review.reviewer?.name}` }} · {{ timeAgo(order.review.created_at) }}</p>
            </div>
            <form v-else-if="isBuyer" @submit.prevent="act('review', { rating, comment }, 'Thanks for your review!')">
              <p class="small muted">How was your experience with {{ order.seller?.name }}?</p>
              <StarRating v-model="rating" editable :size="28" />
              <textarea v-model="comment" class="input mt" rows="3" maxlength="1000" placeholder="Was the item as described? Was the seller on time?"></textarea>
              <button class="btn btn-primary mt" :disabled="working">Submit review</button>
            </form>
            <p v-else class="muted small">The buyer hasn't left a review yet.</p>
          </section>
        </div>

        <aside>
          <section class="card card-body">
            <h3>Delivery</h3>
            <p class="small"><strong>{{ order.delivery_method_label }}</strong></p>
            <p v-if="order.delivery_address" class="small">{{ order.delivery_address }}</p>
            <p v-if="order.contact_phone" class="small">{{ isBuyer ? 'Your phone' : 'Buyer phone' }}: <strong>{{ order.contact_phone }}</strong></p>
            <p v-if="order.seller_phone && isBuyer" class="small">Seller phone: <strong>{{ order.seller_phone }}</strong></p>
            <p v-if="isSeller && !order.contact_phone" class="tiny muted">The buyer's phone and address appear after you accept.</p>
            <p v-if="order.buyer_note" class="small note">“{{ order.buyer_note }}”</p>
            <RouterLink v-if="order.listing.status !== 'deleted'" :to="isBuyer ? `/listings/${order.listing.id}` : '/messages'" class="btn btn-sm btn-block mt">
              <AppIcon name="chat" :size="15" /> {{ isBuyer ? 'Message the seller' : 'Open messages' }}
            </RouterLink>
          </section>

          <section class="card card-body mt">
            <h3>Payment</h3>
            <p class="small"><strong>{{ order.payment_method_label }}</strong> ·
              <span :class="order.payment_status === 'paid' ? 'paid' : 'unpaid'">{{ order.payment_status === 'paid' ? 'Paid' : 'Not paid yet' }}</span>
            </p>
            <template v-if="mobilePay && !closed">
              <p v-if="isBuyer && order.status === 'pending'" class="tiny muted">After the seller accepts, send the money to their {{ order.payment_method_label }} number and enter the transaction ID here.</p>
              <p v-if="isBuyer && order.seller_phone && order.payment_status !== 'paid'" class="tiny">Send {{ formatPrice(order.price) }} to <strong>{{ order.seller_phone }}</strong> ({{ order.payment_method_label }}).</p>
              <p v-if="order.transaction_id" class="small">Transaction ID: <code>{{ order.transaction_id }}</code></p>
              <form v-if="isBuyer && ['accepted', 'shipped'].includes(order.status) && order.payment_status !== 'paid'" class="row" @submit.prevent="act('payment', { transaction_id: trx }, 'Payment details sent to the seller.')">
                <input v-model="trx" class="input" maxlength="40" placeholder="Transaction ID" style="flex: 1" />
                <button class="btn btn-sm" :disabled="working || trx.trim().length < 6">Submit</button>
              </form>
            </template>
            <button v-if="isSeller && ['accepted', 'shipped', 'completed'].includes(order.status) && order.payment_status !== 'paid'"
                    class="btn btn-sm btn-block" :disabled="working" @click="act('confirm-payment', {}, 'Payment confirmed.')">
              Confirm payment received
            </button>
            <p class="tiny muted mt" style="margin-bottom: 0">ResaleIQ does not hold money. Payments go directly between buyer and seller.</p>
          </section>
        </aside>
      </div>
    </template>

    <ModalDialog v-if="dialog" :title="dialog === 'decline' ? 'Decline order' : 'Cancel order'" @close="dialog = ''">
      <div class="form-group">
        <label for="o-reason">Reason <span class="muted">(optional, shared with the other person)</span></label>
        <textarea id="o-reason" v-model="reason" class="input" rows="3" maxlength="500"></textarea>
      </div>
      <template #footer>
        <button class="btn" @click="dialog = ''">Back</button>
        <button class="btn btn-danger" :disabled="working" @click="act(dialog, { reason }, dialog === 'decline' ? 'Order declined.' : 'Order cancelled.')">
          {{ dialog === 'decline' ? 'Decline' : 'Cancel order' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.back { display: inline-flex; align-items: center; gap: 4px; margin-bottom: 10px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 20px; align-items: start; }
.item { display: flex; gap: 16px; align-items: center; }
.thumb.huge { width: 120px; height: 90px; }
.grow { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.price.big { font-size: 1.4rem; }
.steps { list-style: none; padding: 0; margin: 0 0 8px; }
.steps li { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 10px; padding: 8px 0; color: var(--muted); }
.steps li.done { color: var(--text); font-weight: 600; }
.mark { width: 22px; height: 22px; border-radius: 999px; border: 2px solid #cfd6de; display: grid; place-items: center; }
.done .mark { background: var(--primary); border-color: var(--primary); color: #fff; }
.actions { border-top: 1px solid var(--border); padding-top: 14px; margin-top: 6px; }
.actions:empty { display: none; }
.note { background: var(--bg); padding: 8px 10px; border-radius: 8px; }
.paid { color: #166534; font-weight: 600; }
.unpaid { color: #b45309; font-weight: 600; }
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
}
</style>
