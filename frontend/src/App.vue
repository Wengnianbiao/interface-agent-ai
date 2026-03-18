<script setup>
import { onMounted, ref } from 'vue'
import AuthView from './components/AuthView.vue'
import ChatView from './components/ChatView.vue'

const API_BASE_URL = ''
const AUTH_STORAGE_KEY = 'interface-agent-access-token'

const authEnabled = ref(true)
const authInitializing = ref(true)
const accessToken = ref(localStorage.getItem(AUTH_STORAGE_KEY) || '')
const currentUser = ref(null)

const setAccessToken = (token) => {
  accessToken.value = token
  if (token) {
    localStorage.setItem(AUTH_STORAGE_KEY, token)
  } else {
    localStorage.removeItem(AUTH_STORAGE_KEY)
  }
}

const loadHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    if (!response.ok) {
      authEnabled.value = true
      return
    }
    const data = await response.json()
    authEnabled.value = !!data?.authEnabled
  } catch (_error) {
    authEnabled.value = true
  }
}

const fetchCurrentUser = async () => {
  if (!accessToken.value) {
    currentUser.value = null
    return
  }
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken.value}`
      }
    })
    if (!response.ok) {
      setAccessToken('')
      currentUser.value = null
      return
    }
    currentUser.value = await response.json()
  } catch (_error) {
    setAccessToken('')
    currentUser.value = null
  }
}

const handleAuthenticated = (payload) => {
  setAccessToken(payload?.accessToken || '')
  currentUser.value = payload?.user || null
}

const handleLogout = () => {
  setAccessToken('')
  currentUser.value = null
}

onMounted(async () => {
  try {
    await loadHealth()
    if (authEnabled.value) {
      await fetchCurrentUser()
    } else {
      currentUser.value = { username: '本地用户' }
    }
  } finally {
    authInitializing.value = false
  }
})
</script>

<template>
  <AuthView
    v-if="!authInitializing && authEnabled && !currentUser"
    :api-base-url="API_BASE_URL"
    @authenticated="handleAuthenticated"
  />
  <ChatView
    v-else-if="!authInitializing"
    :access-token="accessToken"
    :current-user="currentUser"
    @logout="handleLogout"
  />
</template>

<style>
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body,
#app {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
