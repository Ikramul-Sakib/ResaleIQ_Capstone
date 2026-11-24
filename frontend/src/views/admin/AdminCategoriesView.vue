<script setup>
import { onMounted, reactive, ref } from 'vue'
import api, { errorMessage } from '@/api'
import AdminNav from '@/components/AdminNav.vue'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
const categories = ref([])
const loading = ref(true)
const form = reactive({ name: '', depreciation_rate: 0.2 })
const editing = ref(null)

async function load() {
  try {
    categories.value = (await api.get('/categories')).data
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    loading.value = false
  }
}

async function create() {
  try {
    await api.post('/admin/categories', form)
    toast.show(`Category "${form.name}" added.`)
    Object.assign(form, { name: '', depreciation_rate: 0.2 })
    load()
  } catch (err) {
    toast.error(errorMessage(err))
  }
}

async function save() {
  try {
    await api.put(`/admin/categories/${editing.value.id}`, editing.value)
    toast.show('Category updated.')
    editing.value = null
    load()
  } catch (err) {
    toast.error(errorMessage(err))
  }
}

async function remove(category) {
  try {
    await api.delete(`/admin/categories/${category.id}`)
    toast.show(`Category "${category.name}" deleted.`)
    load()
  } catch (err) {
    toast.error(errorMessage(err))
  }
}

onMounted(load)
</script>

<template>
  <div class="container page">
    <AdminNav />
    <form class="card card-body row mb" @submit.prevent="create">
      <div class="grow">
        <label for="c-name" class="label">New category</label>
        <input id="c-name" v-model="form.name" class="input" placeholder="e.g. Musical Instruments" maxlength="80" required />
      </div>
      <div>
        <label for="c-rate" class="label">Yearly depreciation</label>
        <input id="c-rate" v-model="form.depreciation_rate" class="input" type="number" min="0" max="0.9" step="0.01" style="width: 140px" />
      </div>
      <button class="btn btn-primary add">Add category</button>
    </form>
    <p class="hint mb">Yearly depreciation (0–0.9) is used by the rule-based price estimator, e.g. 0.30 means items lose about 30% of their value per year.</p>

    <div v-if="loading" class="spinner"></div>
    <div v-else class="card table-wrap">
      <table class="table">
        <thead><tr><th>Name</th><th>Live listings</th><th>Yearly depreciation</th><th></th></tr></thead>
        <tbody>
          <tr v-for="category in categories" :key="category.id">
            <template v-if="editing?.id === category.id">
              <td><input v-model="editing.name" class="input" maxlength="80" /></td>
              <td>{{ category.listing_count }}</td>
              <td><input v-model="editing.depreciation_rate" class="input" type="number" min="0" max="0.9" step="0.01" style="width: 110px" /></td>
              <td class="row">
                <button class="btn btn-primary btn-sm" @click="save">Save</button>
                <button class="btn btn-sm btn-ghost" @click="editing = null">Cancel</button>
              </td>
            </template>
            <template v-else>
              <td>{{ category.name }}</td>
              <td>{{ category.listing_count }}</td>
              <td>{{ Math.round(category.depreciation_rate * 100) }}%</td>
              <td class="row">
                <button class="btn btn-sm" @click="editing = { ...category }">Edit</button>
                <button class="btn btn-sm btn-ghost" @click="remove(category)">Delete</button>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.grow { flex: 1; min-width: 200px; }
.add { align-self: flex-end; }
</style>
