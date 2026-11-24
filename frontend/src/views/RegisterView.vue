<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, fieldErrors } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()
const form = reactive({ name: '', email: '', password: '', confirm: '' })
const errors = ref({})
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  errors.value = {}
  if (form.password !== form.confirm) {
    errors.value = { confirm: 'Passwords do not match.' }
    return
  }
  loading.value = true
  try {
    await auth.register({ name: form.name, email: form.email, password: form.password })
    toast.show(`Welcome to ResaleIQ, ${auth.user.name}!`)
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') && !route.query.redirect.startsWith('//') ? route.query.redirect : '/'
    router.replace(redirect)
  } catch (err) {
    errors.value = fieldErrors(err)
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container page">
    <div class="narrow card card-body">
      <h1>Create your account</h1>
      <p class="muted">Sell your used items and find great deals near you.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <form novalidate @submit.prevent="submit">
        <div class="form-group">
          <label for="name">Full name</label>
          <input id="name" v-model="form.name" class="input" :class="{ 'has-error': errors.name }" autocomplete="name" />
          <div v-if="errors.name" class="field-error">{{ errors.name }}</div>
        </div>
        <div class="form-group">
          <label for="email">Email</label>
          <input id="email" v-model="form.email" class="input" :class="{ 'has-error': errors.email }" type="email" autocomplete="email" />
          <div v-if="errors.email" class="field-error">{{ errors.email }}</div>
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input id="password" v-model="form.password" class="input" :class="{ 'has-error': errors.password }" type="password" autocomplete="new-password" />
          <div v-if="errors.password" class="field-error">{{ errors.password }}</div>
          <div v-else class="hint">At least 8 characters, with a letter and a number.</div>
        </div>
        <div class="form-group">
          <label for="confirm">Confirm password</label>
          <input id="confirm" v-model="form.confirm" class="input" :class="{ 'has-error': errors.confirm }" type="password" autocomplete="new-password" />
          <div v-if="errors.confirm" class="field-error">{{ errors.confirm }}</div>
        </div>
        <button class="btn btn-primary btn-block" :disabled="loading">{{ loading ? 'Creating account…' : 'Sign up' }}</button>
      </form>
      <p class="center mt small">Already have an account? <RouterLink :to="{ name: 'login', query: route.query }">Log in</RouterLink></p>
    </div>
  </div>
</template>
