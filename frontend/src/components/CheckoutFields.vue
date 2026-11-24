<script setup>
import { computed } from 'vue'
import { DELIVERY_METHODS, PAYMENT_METHODS } from '@/utils'

// v-model object: { delivery_method, delivery_address, contact_phone, payment_method, note }
const model = defineModel({ type: Object, required: true })
defineProps({ errors: { type: Object, default: () => ({}) } })

const paymentHint = computed(() => PAYMENT_METHODS.find((m) => m.value === model.value.payment_method)?.hint)
const deliveryHint = computed(() => DELIVERY_METHODS.find((m) => m.value === model.value.delivery_method)?.hint)
</script>

<template>
  <div>
    <div class="form-group">
      <span class="label">Delivery</span>
      <div class="options">
        <label v-for="m in DELIVERY_METHODS" :key="m.value" class="option" :class="{ selected: model.delivery_method === m.value }">
          <input v-model="model.delivery_method" type="radio" name="delivery" :value="m.value" />
          {{ m.label }}
        </label>
      </div>
      <div class="hint">{{ deliveryHint }}</div>
    </div>
    <div v-if="model.delivery_method === 'delivery'" class="form-group">
      <label for="co-address">Delivery address</label>
      <textarea id="co-address" v-model="model.delivery_address" class="input" :class="{ 'has-error': errors.delivery_address }" rows="2" maxlength="300" placeholder="House, road, area, city"></textarea>
      <div v-if="errors.delivery_address" class="field-error">{{ errors.delivery_address }}</div>
    </div>
    <div class="form-group">
      <label for="co-phone">Your phone number</label>
      <input id="co-phone" v-model="model.contact_phone" class="input" :class="{ 'has-error': errors.contact_phone }" maxlength="30" placeholder="01XXX-XXXXXX" />
      <div v-if="errors.contact_phone" class="field-error">{{ errors.contact_phone }}</div>
      <div v-else class="hint">Shared with the seller only after they accept your order.</div>
    </div>
    <div class="form-group">
      <span class="label">Payment</span>
      <div class="options">
        <label v-for="m in PAYMENT_METHODS" :key="m.value" class="option" :class="{ selected: model.payment_method === m.value }">
          <input v-model="model.payment_method" type="radio" name="payment" :value="m.value" />
          {{ m.label }}
        </label>
      </div>
      <div class="hint">{{ paymentHint }}</div>
    </div>
    <div class="form-group">
      <label for="co-note">Note to seller <span class="muted">(optional)</span></label>
      <input id="co-note" v-model="model.note" class="input" maxlength="500" placeholder="e.g. Can we meet near Dhanmondi 27?" />
    </div>
  </div>
</template>

<style scoped>
.options { display: flex; gap: 8px; flex-wrap: wrap; }
.option { display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border: 1px solid #cfd6de; border-radius: 8px; cursor: pointer; font-size: 0.92rem; }
.option.selected { border-color: var(--primary); background: var(--primary-soft); }
.option input { accent-color: var(--primary); }
</style>
