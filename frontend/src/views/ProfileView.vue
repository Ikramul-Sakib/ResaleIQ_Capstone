<script setup>
import { reactive, ref } from 'vue'
import api, { errorMessage, fieldErrors, tokenStorage } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { LOCATIONS } from '@/utils'

const auth = useAuthStore()
const toast = useToastStore()

const profile = reactive({
  name: auth.user.name,
  phone: auth.user.phone || '',
  location: auth.user.location || '',
  bio: auth.user.bio || '',
})
const profileErrors = ref({})
const savingProfile = ref(false)

const passwords = reactive({ current_password: '', new_password: '', confirm: '' })
const passwordErrors = ref({})
const savingPassword = ref(false)

async function saveProfile() {
  profileErrors.value = {}
  savingProfile.value = true
  try {
    const { data } = await api.put('/users/me', profile)
    auth.user = data.user
    toast.show('Profile saved.')
  } catch (err) {
    profileErrors.value = fieldErrors(err)
    toast.error(errorMessage(err))
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  passwordErrors.value = {}
  if (passwords.new_password !== passwords.confirm) {
    passwordErrors.value = { confirm: 'Passwords do not match.' }
    return
  }
  savingPassword.value = true
  try {
    const { data } = await api.put('/users/me/password', {
      current_password: passwords.current_password,
      new_password: passwords.new_password,
    })
    tokenStorage.set(data.token)
    Object.assign(passwords, { current_password: '', new_password: '', confirm: '' })
    toast.show('Password changed. Other devices have been logged out.')
  } catch (err) {
    passwordErrors.value = fieldErrors(err)
    toast.error(errorMessage(err))
  } finally {
    savingPassword.value = false
  }
}
</script>

<template>
  <div class="container page medium">
    <div class="page-header">
      <div>
        <h1>Profile</h1>
        <p>Buyers see your name, location and description.</p>
      </div>
      <RouterLink :to="`/sellers/${auth.user.id}`" class="btn btn-sm">View public profile</RouterLink>
    </div>

    <form class="card card-body" novalidate @submit.prevent="saveProfile">
      <h2>Your details</h2>
      <div class="form-grid">
        <div class="form-group">
          <label for="p-name">Name</label>
          <input id="p-name" v-model="profile.name" class="input" :class="{ 'has-error': profileErrors.name }" maxlength="100" />
          <div v-if="profileErrors.name" class="field-error">{{ profileErrors.name }}</div>
        </div>
        <div class="form-group">
          <label for="p-email">Email</label>
          <input id="p-email" :value="auth.user.email" class="input" disabled />
        </div>
        <div class="form-group">
          <label for="p-phone">Phone</label>
          <input id="p-phone" v-model="profile.phone" class="input" maxlength="30" placeholder="01XXX-XXXXXX" />
        </div>
        <div class="form-group">
          <label for="p-location">Location</label>
          <input id="p-location" v-model="profile.location" class="input" list="p-locations" maxlength="100" />
          <datalist id="p-locations"><option v-for="l in LOCATIONS" :key="l" :value="l" /></datalist>
        </div>
        <div class="form-group full">
          <label for="p-bio">About you</label>
          <textarea id="p-bio" v-model="profile.bio" class="input" rows="3" maxlength="500"></textarea>
        </div>
      </div>
      <button class="btn btn-primary" :disabled="savingProfile">Save profile</button>
    </form>

    <form class="card card-body mt" novalidate @submit.prevent="changePassword">
      <h2>Change password</h2>
      <div class="form-group">
        <label for="c-current">Current password</label>
        <input id="c-current" v-model="passwords.current_password" class="input" type="password" autocomplete="current-password" />
        <div v-if="passwordErrors.current_password" class="field-error">{{ passwordErrors.current_password }}</div>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label for="c-new">New password</label>
          <input id="c-new" v-model="passwords.new_password" class="input" type="password" autocomplete="new-password" />
          <div v-if="passwordErrors.new_password" class="field-error">{{ passwordErrors.new_password }}</div>
        </div>
        <div class="form-group">
          <label for="c-confirm">Confirm new password</label>
          <input id="c-confirm" v-model="passwords.confirm" class="input" type="password" autocomplete="new-password" />
          <div v-if="passwordErrors.confirm" class="field-error">{{ passwordErrors.confirm }}</div>
        </div>
      </div>
      <button class="btn btn-primary" :disabled="savingPassword">Change password</button>
    </form>
  </div>
</template>
