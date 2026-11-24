<script setup>
import { computed, onMounted, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import api, { errorMessage, fieldErrors } from '@/api'
import { formatPrice } from '@/utils'

// Product details come from the listing form; the estimator asks for purchase price and age.
const props = defineProps({
  product: { type: Object, required: true },
  listingId: { type: [Number, String], default: null },
})
const emit = defineEmits(['use-price'])

const originalPrice = ref('')
const ageMonths = ref('')
const result = ref(null)
const error = ref('')
const errors = ref({})
const loading = ref(false)
const aiEnabled = ref(null)

const missing = computed(() => {
  const list = []
  if (!props.product.title || props.product.title.trim().length < 3) list.push('product title')
  if (!props.product.category_id) list.push('category')
  if (!props.product.condition) list.push('condition')
  return list
})

const position = computed(() => {
  if (!result.value) return 50
  const { min_price: low, max_price: high, recommended_price: rec } = result.value
  return high === low ? 50 : ((rec - low) / (high - low)) * 100
})

onMounted(async () => {
  try {
    aiEnabled.value = (await api.get('/ai/status')).data.ai_enabled
  } catch {
    aiEnabled.value = false
  }
})

async function estimate() {
  error.value = ''
  errors.value = {}
  if (missing.value.length) {
    error.value = `Fill in the ${missing.value.join(', ')} first.`
    return
  }
  loading.value = true
  try {
    const { data } = await api.post('/ai/estimate-price', {
      title: props.product.title,
      category_id: Number(props.product.category_id),
      condition: props.product.condition,
      brand: props.product.brand,
      model: props.product.model,
      description: (props.product.description || '').slice(0, 1000),
      original_price: originalPrice.value || null,
      age_months: ageMonths.value === '' ? null : ageMonths.value,
      listing_id: props.listingId ? Number(props.listingId) : null,
    })
    result.value = data
  } catch (err) {
    errors.value = fieldErrors(err)
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="estimator card">
    <div class="head">
      <AppIcon name="sparkle" :size="20" />
      <div>
        <h3>AI price estimate</h3>
        <p class="tiny">Get a fair price range in Taka before you post.</p>
      </div>
    </div>
    <div class="card-body">
      <div class="form-grid">
        <div class="form-group">
          <label for="orig">Original price (৳)</label>
          <input id="orig" v-model="originalPrice" class="input" :class="{ 'has-error': errors.original_price }" type="number" min="1" placeholder="e.g. 85000" />
        </div>
        <div class="form-group">
          <label for="age">Age (months)</label>
          <input id="age" v-model="ageMonths" class="input" type="number" min="0" max="600" placeholder="e.g. 18" />
        </div>
      </div>
      <p class="hint" style="margin-top: -6px">Uses the title, category, brand, model and condition from the form.</p>
      <button type="button" class="btn btn-primary btn-block" :disabled="loading" @click="estimate">
        <AppIcon name="sparkle" :size="16" /> {{ loading ? 'Estimating…' : 'Estimate price' }}
      </button>
      <div v-if="error" class="alert alert-error mt">{{ error }}</div>

      <div v-if="result" class="result">
        <div class="row between">
          <span class="badge" :class="result.source === 'ai' ? 'badge-ai' : ''">
            {{ result.source === 'ai' ? 'AI estimate' : 'Rule-based estimate' }}
          </span>
          <span class="tiny muted">Confidence: {{ result.confidence }}</span>
        </div>
        <div class="recommended">{{ formatPrice(result.recommended_price) }}</div>
        <div class="tiny muted center">Recommended price</div>
        <div class="range" aria-hidden="true">
          <div class="bar"><span class="marker" :style="{ left: `${position}%` }"></span></div>
          <div class="row between tiny">
            <span>{{ formatPrice(result.min_price) }}</span>
            <span>{{ formatPrice(result.max_price) }}</span>
          </div>
        </div>
        <ul class="why small">
          <li v-for="(reason, index) in result.explanation" :key="index">{{ reason }}</li>
        </ul>
        <p v-if="result.notice" class="tiny muted">{{ result.notice }}</p>
        <button type="button" class="btn btn-accent btn-block" @click="emit('use-price', result.recommended_price)">
          Use {{ formatPrice(result.recommended_price) }}
        </button>
        <p class="tiny muted mt" style="margin-bottom: 0">Estimates are advice only. You decide the final price.</p>
      </div>
      <p v-else-if="aiEnabled === false" class="tiny muted mt" style="margin-bottom: 0">
        AI is not connected yet, so estimates use depreciation rules and similar listings on ResaleIQ.
      </p>
    </div>
  </div>
</template>

<style scoped>
.estimator { overflow: hidden; }
.head { display: flex; gap: 10px; align-items: center; padding: 14px 20px; background: linear-gradient(135deg, #f3efff, #e6f4f2); color: #4c1d95; }
.head h3 { margin: 0; color: var(--text); }
.head p { margin: 0; color: var(--muted); }
.result { margin-top: 16px; border-top: 1px solid var(--border); padding-top: 14px; }
.recommended { font-size: 1.8rem; font-weight: 800; color: var(--primary-dark); text-align: center; margin-top: 6px; }
.range { margin: 12px 0; }
.bar { position: relative; height: 8px; border-radius: 999px; background: linear-gradient(90deg, #fde68a, #34d399, #fde68a); margin-bottom: 6px; }
.marker { position: absolute; top: -5px; width: 18px; height: 18px; border-radius: 999px; background: #fff; border: 3px solid var(--primary); transform: translateX(-50%); }
.why { padding-left: 18px; margin: 8px 0; }
.why li { margin-bottom: 4px; }
</style>
