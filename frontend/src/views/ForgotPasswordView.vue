<script setup>
import { ref } from 'vue'
import api, { errorMessage } from '@/api'

const email = ref('')
const done = ref('')
const devLink = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const { data } = await api.post('/auth/forgot-password', { email: email.value })
    done.value = data.message
    devLink.value = data.dev_reset_link || ''
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function localPath(link) {
  try {
    const url = new URL(link)
    return url.pathname + url.search
  } catch {
    return link
  }
}
</script>

<template>
  <div class="container page">
    <div class="narrow card card-body">
      <h1>Forgot your password?</h1>
      <template v-if="done">
        <div class="alert alert-success">{{ done }}</div>
        <div v-if="devLink" class="alert alert-info small">
          <strong>Development mode:</strong> email sending is not set up, so here is the reset link:
          <RouterLink :to="localPath(devLink)">Reset my password</RouterLink>
        </div>
      </template>
      <template v-else>
        <p class="muted">Enter your email and we'll send you a link to set a new password.</p>
        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <form @submit.prevent="submit">
          <div class="form-group">
            <label for="email">Email</label>
            <input id="email" v-model="email" class="input" type="email" required autocomplete="email" />
          </div>
          <button class="btn btn-primary btn-block" :disabled="loading">Send reset link</button>
        </form>
      </template>
      <p class="center mt small"><RouterLink to="/login">Back to log in</RouterLink></p>
    </div>
  </div>
</template>
