<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import api, { errorMessage, fieldErrors } from '@/api'

const route = useRoute()
const password = ref('')
const confirm = ref('')
const errors = ref({})
const error = ref('')
const done = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  errors.value = {}
  if (password.value !== confirm.value) {
    errors.value = { confirm: 'Passwords do not match.' }
    return
  }
  loading.value = true
  try {
    const { data } = await api.post('/auth/reset-password', { token: route.query.token, password: password.value })
    done.value = data.message
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
      <h1>Set a new password</h1>
      <div v-if="!route.query.token" class="alert alert-error">This reset link is incomplete. Request a new one.</div>
      <template v-else-if="done">
        <div class="alert alert-success">{{ done }}</div>
        <RouterLink to="/login" class="btn btn-primary btn-block">Log in</RouterLink>
      </template>
      <form v-else novalidate @submit.prevent="submit">
        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <div class="form-group">
          <label for="password">New password</label>
          <input id="password" v-model="password" class="input" type="password" autocomplete="new-password" />
          <div v-if="errors.password" class="field-error">{{ errors.password }}</div>
          <div v-else class="hint">At least 8 characters, with a letter and a number.</div>
        </div>
        <div class="form-group">
          <label for="confirm">Confirm new password</label>
          <input id="confirm" v-model="confirm" class="input" type="password" autocomplete="new-password" />
          <div v-if="errors.confirm" class="field-error">{{ errors.confirm }}</div>
        </div>
        <button class="btn btn-primary btn-block" :disabled="loading">Save new password</button>
      </form>
    </div>
  </div>
</template>
