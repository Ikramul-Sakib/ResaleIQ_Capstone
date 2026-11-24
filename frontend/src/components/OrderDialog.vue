<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { errorMessage, fieldErrors } from '@/api'
import CheckoutFields from './CheckoutFields.vue'
import ModalDialog from './ModalDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { formatPrice } from '@/utils'

const props = defineProps({
  listing: { type: Object, required: true },
  mode: { type: String, default: 'buy' }, // buy | offer
})
const emit = defineEmits(['close'])

const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()

const checkout = reactive({
  delivery_method: 'meetup',
  delivery_address: '',
  contact_phone: auth.user?.phone || '',
  payment_method: 'cod',
  note: '',
})
const offer = ref(Math.round(props.listing.price * 0.9))
const errors = ref({})
const error = ref('')
const saving = ref(false)

const minimumOffer = computed(() => Math.ceil(props.listing.price * 0.5))

async function submit() {
  errors.value = {}
  error.value = ''
  saving.value = true
  try {
    const body = { listing_id: props.listing.id, ...checkout }
    if (props.mode === 'offer') body.offer_price = offer.value
    const { data } = await api.post('/orders', body)
    toast.show(props.mode === 'offer' ? 'Offer sent! The seller will reply soon.' : 'Order placed! Waiting for the seller to accept.')
    auth.refreshSummary()
    router.push(`/orders/${data.id}`)
  } catch (err) {
    errors.value = fieldErrors(err)
    error.value = errorMessage(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ModalDialog :title="mode === 'offer' ? 'Make an offer' : 'Buy now'" @close="emit('close')">
    <div class="summary">
      <strong class="truncate">{{ listing.title }}</strong>
      <span class="price">{{ formatPrice(listing.price) }}</span>
    </div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="mode === 'offer'" class="form-group">
      <label for="offer">Your offer (৳)</label>
      <input id="offer" v-model.number="offer" class="input" :class="{ 'has-error': errors.offer_price }" type="number" :min="minimumOffer" :max="listing.price" />
      <div v-if="errors.offer_price" class="field-error">{{ errors.offer_price }}</div>
      <div v-else class="hint">Asking price {{ formatPrice(listing.price) }}. Offers must be at least {{ formatPrice(minimumOffer) }}.</div>
    </div>
    <CheckoutFields v-model="checkout" :errors="errors" />
    <p class="tiny muted" style="margin: 0">
      Nothing is charged now. The seller accepts or declines; the item is then reserved for you.
    </p>
    <template #footer>
      <button class="btn" @click="emit('close')">Cancel</button>
      <button class="btn btn-primary" :disabled="saving" @click="submit">
        {{ saving ? 'Sending…' : mode === 'offer' ? `Send offer of ${formatPrice(offer || 0)}` : `Place order · ${formatPrice(listing.price)}` }}
      </button>
    </template>
  </ModalDialog>
</template>

<style scoped>
.summary { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; background: var(--bg); border-radius: 8px; margin-bottom: 14px; }
</style>
