<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { errorMessage, fieldErrors } from '@/api'
import ImagePicker from '@/components/ImagePicker.vue'
import PriceEstimator from '@/components/PriceEstimator.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { CONDITIONS, LOCATIONS } from '@/utils'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

const editId = computed(() => route.params.id || null)
const categories = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const errors = ref({})
const existingImages = ref([])
const newFiles = ref([])
const status = ref('')

const form = reactive({
  title: '',
  category_id: '',
  condition: '',
  price: '',
  brand: '',
  model: '',
  location: auth.user?.location || '',
  description: '',
})

onMounted(async () => {
  try {
    categories.value = (await api.get('/categories')).data
    if (editId.value) {
      const { data } = await api.get(`/listings/${editId.value}`)
      if (!data.is_owner) {
        router.replace(`/listings/${editId.value}`)
        return
      }
      Object.assign(form, {
        title: data.title,
        category_id: data.category?.id || '',
        condition: data.condition,
        price: data.price,
        brand: data.brand || '',
        model: data.model || '',
        location: data.location,
        description: data.description,
      })
      existingImages.value = data.images
      status.value = data.status
    }
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
})

async function submit() {
  error.value = ''
  errors.value = {}
  const body = new FormData()
  for (const [key, value] of Object.entries(form)) body.append(key, value ?? '')
  existingImages.value.forEach((image) => body.append('keep_images', image.id))
  newFiles.value.forEach((file) => body.append('images', file, file.name))

  saving.value = true
  try {
    const { data } = editId.value
      ? await api.put(`/listings/${editId.value}`, body)
      : await api.post('/listings', body)
    toast.show(editId.value ? 'Changes saved and sent for review.' : 'Listing submitted! It will go live after admin review.')
    router.push(`/listings/${data.id}`)
  } catch (err) {
    errors.value = fieldErrors(err)
    error.value = errorMessage(err)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="container page">
    <div class="page-header">
      <div>
        <h1>{{ editId ? 'Edit listing' : 'Sell an item' }}</h1>
        <p>Listings are checked by our team before they go live, usually within a day.</p>
      </div>
    </div>

    <div v-if="loading" class="spinner"></div>
    <div v-else class="layout">
      <form class="card card-body" novalidate @submit.prevent="submit">
        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div v-if="editId && ['approved', 'rejected'].includes(status)" class="alert alert-warning">
          Saving changes sends this listing back for admin review.
        </div>

        <div class="form-group">
          <span class="label">Photos</span>
          <ImagePicker v-model:existing="existingImages" v-model:files="newFiles" :error="errors.images" />
        </div>

        <div class="form-group">
          <label for="title">Title</label>
          <input id="title" v-model="form.title" class="input" :class="{ 'has-error': errors.title }" maxlength="120" placeholder="e.g. Samsung Galaxy S21 8/128GB, Phantom Grey" />
          <div v-if="errors.title" class="field-error">{{ errors.title }}</div>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label for="category">Category</label>
            <select id="category" v-model="form.category_id" class="input" :class="{ 'has-error': errors.category_id }">
              <option value="" disabled>Choose a category</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <div v-if="errors.category_id" class="field-error">{{ errors.category_id }}</div>
          </div>
          <div class="form-group">
            <label for="condition">Condition</label>
            <select id="condition" v-model="form.condition" class="input" :class="{ 'has-error': errors.condition }">
              <option value="" disabled>Choose condition</option>
              <option v-for="c in CONDITIONS" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
            <div v-if="errors.condition" class="field-error">{{ errors.condition }}</div>
          </div>
          <div class="form-group">
            <label for="brand">Brand <span class="muted">(optional)</span></label>
            <input id="brand" v-model="form.brand" class="input" maxlength="80" placeholder="e.g. Samsung" />
          </div>
          <div class="form-group">
            <label for="model">Model <span class="muted">(optional)</span></label>
            <input id="model" v-model="form.model" class="input" maxlength="80" placeholder="e.g. Galaxy S21" />
          </div>
          <div class="form-group">
            <label for="price">Price (৳)</label>
            <input id="price" v-model="form.price" class="input" :class="{ 'has-error': errors.price }" type="number" min="1" placeholder="e.g. 35000" />
            <div v-if="errors.price" class="field-error">{{ errors.price }}</div>
          </div>
          <div class="form-group">
            <label for="location">Location</label>
            <input id="location" v-model="form.location" class="input" :class="{ 'has-error': errors.location }" list="form-locations" maxlength="100" placeholder="e.g. Dhaka" />
            <datalist id="form-locations"><option v-for="l in LOCATIONS" :key="l" :value="l" /></datalist>
            <div v-if="errors.location" class="field-error">{{ errors.location }}</div>
          </div>
        </div>

        <div class="form-group">
          <label for="description">Description</label>
          <textarea id="description" v-model="form.description" class="input" :class="{ 'has-error': errors.description }" rows="6" maxlength="5000" placeholder="Describe the item: how long you used it, any defects, what's included, reason for selling…"></textarea>
          <div v-if="errors.description" class="field-error">{{ errors.description }}</div>
        </div>

        <div class="row">
          <button class="btn btn-primary" :disabled="saving">{{ saving ? 'Uploading…' : editId ? 'Save changes' : 'Submit for review' }}</button>
          <RouterLink :to="editId ? `/listings/${editId}` : '/'" class="btn btn-ghost">Cancel</RouterLink>
        </div>
      </form>

      <aside class="side">
        <PriceEstimator :product="form" :listing-id="editId" @use-price="(p) => { form.price = p; toast.show('Price applied to your listing.') }" />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: start; }
.side { position: sticky; top: 80px; }
@media (max-width: 960px) {
  .layout { grid-template-columns: 1fr; }
  .side { position: static; }
}
</style>
