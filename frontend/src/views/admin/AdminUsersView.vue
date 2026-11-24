<script setup>
import { onMounted, ref } from 'vue'
import api, { errorMessage } from '@/api'
import AdminNav from '@/components/AdminNav.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import { useToastStore } from '@/stores/toast'
import { formatDate } from '@/utils'

const toast = useToastStore()
const search = ref('')
const page = ref(1)
const data = ref({ items: [], page: 1, pages: 0, total: 0 })
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  try {
    data.value = (await api.get('/admin/users', { params: { q: search.value, page: page.value } })).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function toggleBlock(user) {
  const action = user.is_blocked ? 'unblock' : 'block'
  try {
    const { data: updated } = await api.post(`/admin/users/${user.id}/${action}`)
    user.is_blocked = updated.is_blocked
    toast.show(`${user.name} was ${action}ed.`)
  } catch (err) {
    toast.error(errorMessage(err))
  }
}

onMounted(load)
</script>

<template>
  <div class="container page">
    <AdminNav />
    <form class="row mb" @submit.prevent="page = 1; load()">
      <input v-model="search" class="input" type="search" placeholder="Search by name or email" style="max-width: 320px" />
      <button class="btn">Search</button>
      <span class="muted small">{{ data.total }} users</span>
    </form>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="spinner"></div>
    <div v-else class="card table-wrap">
      <table class="table">
        <thead>
          <tr><th>Name</th><th>Email</th><th>Location</th><th>Listings</th><th>Joined</th><th>Status</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="user in data.items" :key="user.id">
            <td><RouterLink :to="`/sellers/${user.id}`">{{ user.name }}</RouterLink></td>
            <td>{{ user.email }}</td>
            <td>{{ user.location || '—' }}</td>
            <td>{{ user.listing_count }}</td>
            <td>{{ formatDate(user.member_since) }}</td>
            <td>
              <span v-if="user.role === 'admin'" class="badge badge-ai">Admin</span>
              <span v-else-if="user.is_blocked" class="badge badge-rejected">Blocked</span>
              <span v-else class="badge badge-approved">Active</span>
            </td>
            <td>
              <button v-if="user.role !== 'admin'" class="btn btn-sm" :class="{ 'btn-danger': !user.is_blocked }" @click="toggleBlock(user)">
                {{ user.is_blocked ? 'Unblock' : 'Block' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :page="data.page" :pages="data.pages" @change="(p) => { page = p; load() }" />
  </div>
</template>
