<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  apiBaseUrl: {
    type: String,
    default: ''
  }
})
const emit = defineEmits(['authenticated'])

const authMode = ref('login')
const loginUsername = ref('')
const loginPassword = ref('')
const loginError = ref('')
const isLoggingIn = ref(false)
const registerUsername = ref('')
const registerPassword = ref('')
const registerConfirmPassword = ref('')
const registerError = ref('')
const isRegistering = ref(false)
const errorDialogVisible = ref(false)
const errorDialogMessage = ref('')

watch(authMode, () => {
  loginError.value = ''
  registerError.value = ''
})

const showErrorDialog = (message) => {
  errorDialogMessage.value = message || '操作失败'
  errorDialogVisible.value = true
}

const login = async () => {
  if (!loginUsername.value.trim() || !loginPassword.value.trim() || isLoggingIn.value) return
  isLoggingIn.value = true
  loginError.value = ''
  try {
    const response = await fetch(`${props.apiBaseUrl}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: loginUsername.value.trim(),
        password: loginPassword.value
      })
    })
    const payload = await response.json()
    if (!response.ok) {
      if (response.status === 405) {
        throw new Error('后端未加载登录接口，请重启后端服务后重试')
      }
      throw new Error(payload?.detail || `HTTP error! status: ${response.status}`)
    }
    emit('authenticated', payload)
    loginPassword.value = ''
  } catch (error) {
    loginError.value = error?.message || '登录失败'
    showErrorDialog(loginError.value)
  } finally {
    isLoggingIn.value = false
  }
}

const register = async () => {
  if (!registerUsername.value.trim() || !registerPassword.value.trim() || isRegistering.value) return
  if (registerPassword.value !== registerConfirmPassword.value) {
    registerError.value = '两次密码输入不一致'
    showErrorDialog(registerError.value)
    return
  }
  isRegistering.value = true
  registerError.value = ''
  try {
    const response = await fetch(`${props.apiBaseUrl}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: registerUsername.value.trim(),
        password: registerPassword.value
      })
    })
    const payload = await response.json()
    if (!response.ok) {
      if (response.status === 405) {
        throw new Error('后端未加载注册接口，请重启后端服务后重试')
      }
      throw new Error(payload?.detail || `HTTP error! status: ${response.status}`)
    }
    emit('authenticated', payload)
    registerUsername.value = ''
    registerPassword.value = ''
    registerConfirmPassword.value = ''
    authMode.value = 'login'
  } catch (error) {
    registerError.value = error?.message || '注册失败'
    showErrorDialog(registerError.value)
  } finally {
    isRegistering.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="login-card">
      <h2>{{ authMode === 'login' ? '登录系统' : '注册账号' }}</h2>
      <div class="auth-mode-switch">
        <button type="button" class="auth-mode-btn" :class="{ active: authMode === 'login' }" @click="authMode = 'login'">登录</button>
        <button type="button" class="auth-mode-btn" :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
      </div>
      <template v-if="authMode === 'login'">
        <p>请输入账号密码后继续使用聊天能力</p>
        <input
          v-model="loginUsername"
          type="text"
          placeholder="用户名"
          class="login-input"
          @keydown.enter.prevent="login"
        />
        <input
          v-model="loginPassword"
          type="password"
          placeholder="密码"
          class="login-input"
          @keydown.enter.prevent="login"
        />
        <button type="button" class="login-btn" :disabled="isLoggingIn || !loginUsername.trim() || !loginPassword.trim()" @click="login">
          {{ isLoggingIn ? '登录中...' : '登录' }}
        </button>
      </template>
      <template v-else>
        <p>创建账号后将自动登录并进入聊天</p>
        <input
          v-model="registerUsername"
          type="text"
          placeholder="用户名"
          class="login-input"
          @keydown.enter.prevent="register"
        />
        <input
          v-model="registerPassword"
          type="password"
          placeholder="密码（至少6位）"
          class="login-input"
          @keydown.enter.prevent="register"
        />
        <input
          v-model="registerConfirmPassword"
          type="password"
          placeholder="确认密码"
          class="login-input"
          @keydown.enter.prevent="register"
        />
        <button type="button" class="login-btn" :disabled="isRegistering || !registerUsername.trim() || !registerPassword.trim() || !registerConfirmPassword.trim()" @click="register">
          {{ isRegistering ? '注册中...' : '注册并登录' }}
        </button>
      </template>
    </div>
    <div v-if="errorDialogVisible" class="error-dialog-mask" @click="errorDialogVisible = false">
      <div class="error-dialog" @click.stop>
        <div class="error-dialog-header">
          <div class="error-dialog-badge">!</div>
          <div class="error-dialog-title">操作失败</div>
          <button type="button" class="error-dialog-close" @click="errorDialogVisible = false">×</button>
        </div>
        <div class="error-dialog-message">{{ errorDialogMessage }}</div>
        <button type="button" class="error-dialog-btn" @click="errorDialogVisible = false">我知道了</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f7f8fa;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  border: 1px solid #e6e8ef;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.login-card h2 {
  margin: 0;
  font-size: 24px;
}

.login-card p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.auth-mode-switch {
  display: flex;
  gap: 8px;
  background: #f3f5fa;
  padding: 4px;
  border-radius: 10px;
}

.auth-mode-btn {
  flex: 1;
  border: none;
  border-radius: 8px;
  padding: 8px 10px;
  background: transparent;
  color: #5f6780;
  cursor: pointer;
}

.auth-mode-btn.active {
  background: white;
  color: #1f2533;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.1);
}

.login-input {
  border: 1px solid #d8deea;
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 14px;
}

.login-input:focus {
  outline: none;
  border-color: #6b72ff;
  box-shadow: 0 0 0 3px rgba(107, 114, 255, 0.1);
}

.login-btn {
  border: none;
  border-radius: 10px;
  padding: 12px 14px;
  background: #6b72ff;
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.login-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.error-dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.error-dialog {
  width: min(92vw, 420px);
  background: #fff;
  border-radius: 16px;
  border: 1px solid #e6ebff;
  padding: 18px 18px 16px;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.error-dialog-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.error-dialog-badge {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff6b6b 0%, #ff8a4c 100%);
  color: #fff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-dialog-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  flex: 1;
}

.error-dialog-close {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: #f3f4f8;
  color: #4b5563;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.error-dialog-message {
  color: #475569;
  line-height: 1.6;
  white-space: pre-wrap;
  font-size: 15px;
}

.error-dialog-btn {
  border: none;
  border-radius: 12px;
  padding: 11px 14px;
  background: linear-gradient(135deg, #5b6dfb 0%, #6a7dff 100%);
  color: #fff;
  cursor: pointer;
  font-weight: 600;
}
</style>
