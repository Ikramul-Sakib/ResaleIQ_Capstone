<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') && !route.query.redirect.startsWith('//') ? route.query.redirect : '/'
    router.replace(redirect)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container page">
    <div class="narrow card card-body">
      <h1>Log in</h1>
      <p class="muted">Welcome back to ResaleIQ.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label for="email">Email</label>
          <input id="email" v-model="email" class="input" type="email" autocomplete="email" required />
        </div>
        <div class="form-group">
          <div class="row between">
            <label for="password">Password</label>
            <RouterLink to="/forgot-password" class="small">Forgot password?</RouterLink>
          </div>
          <input id="password" v-model="password" class="input" type="password" autocomplete="current-password" required />
        </div>
        <button class="btn btn-primary btn-block" :disabled="loading">{{ loading ? 'Logging in…' : 'Log in' }}</button>
      </form>
      <p class="center mt small">New to ResaleIQ? <RouterLink :to="{ name: 'register', query: route.query }">Create an account</RouterLink></p>
    </div>
  </div>
</template>
