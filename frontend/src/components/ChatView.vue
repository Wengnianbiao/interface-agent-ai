<script setup>
import { ref, nextTick, watch } from 'vue'

const API_BASE_URL = ''
const props = defineProps({
  accessToken: {
    type: String,
    default: ''
  },
  currentUser: {
    type: Object,
    default: null
  }
})
const emit = defineEmits(['logout'])

const messages = ref([])
const inputPrompt = ref('')
const isLoading = ref(false)
const textareaRef = ref(null)
const messagesContainerRef = ref(null)
const isSidebarCollapsed = ref(false)
const sessionId = ref((typeof crypto !== 'undefined' && crypto.randomUUID)
  ? crypto.randomUUID()
  : `${Date.now()}-${Math.random().toString(36).slice(2)}`)

// 清空消息
const clearMessages = () => {
  messages.value = []
  sessionId.value = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

const logout = () => {
  messages.value = []
  inputPrompt.value = ''
  sessionId.value = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`
  emit('logout')
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainerRef.value) {
      messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight
    }
  })
}

// 自动调整文本框高度
const autoResizeTextarea = () => {
  const textarea = textareaRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
  }
}

// 监听输入变化
watch(inputPrompt, () => {
  nextTick(() => {
    autoResizeTextarea()
  })
})

// 发送消息
const sendMessage = async () => {
  if (!inputPrompt.value.trim() || isLoading.value) return
  
  const userMessage = inputPrompt.value.trim()
  let aiMessageIndex = -1
  
  messages.value.push({
    role: 'user',
    content: userMessage
  })
  
  scrollToBottom()
  
  inputPrompt.value = ''
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
    }
  })
  
  isLoading.value = true
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(props.accessToken ? { Authorization: `Bearer ${props.accessToken}` } : {})
      },
      body: JSON.stringify({
        prompt: userMessage,
        sessionId: sessionId.value
      })
    })
    const responseSessionId = response.headers.get('X-Session-Id')
    if (responseSessionId) {
      sessionId.value = responseSessionId
    }
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    
    let fullContent = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value, { stream: true })
      fullContent += chunk
      
      // 第一次收到数据时创建消息
      if (aiMessageIndex === -1) {
        aiMessageIndex = messages.value.length
        messages.value.push({
          role: 'assistant',
          content: fullContent
        })
        isLoading.value = false
      } else {
        messages.value[aiMessageIndex].content = fullContent
      }
      
      scrollToBottom()
    }
  } catch (error) {
    console.error('请求失败:', error)
    if (aiMessageIndex === -1) {
      messages.value.push({
        role: 'assistant',
        content: `❌ 请求失败：${error.message}`
      })
    } else {
      messages.value[aiMessageIndex].content = `❌ 请求失败：${error.message}`
    }
  } finally {
    isLoading.value = false
  }
}

// 解析 Markdown 代码块 - 支持未完成的代码块（流式输出）
const parseContent = (content) => {
  const parts = []
  const regex = /```(\w+)?\n([\s\S]*?)```/g
  let lastIndex = 0
  let match
  
  // 处理已完成的代码块
  while ((match = regex.exec(content)) !== null) {
    // 添加代码块前的文本
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.substring(lastIndex, match.index)
      })
    }
    
    // 添加已完成的代码块
    parts.push({
      type: 'code',
      language: match[1] || 'text',
      content: match[2],
      completed: true
    })
    
    lastIndex = regex.lastIndex
  }
  
  // 处理剩余内容（可能包含未完成的代码块）
  const remaining = content.substring(lastIndex)
  if (remaining) {
    // 检测未完成的代码块（只有开始标记，没有结束标记）
    const incompleteMatch = /```(\w+)?\n([\s\S]*)$/.exec(remaining)
    if (incompleteMatch) {
      // 添加代码块前的文本
      const beforeCode = remaining.substring(0, incompleteMatch.index)
      if (beforeCode) {
        parts.push({
          type: 'text',
          content: beforeCode
        })
      }
      
      // 添加未完成的代码块
      parts.push({
        type: 'code',
        language: incompleteMatch[1] || 'text',
        content: incompleteMatch[2],
        completed: false  // 标记为未完成
      })
    } else {
      // 正常文本
      parts.push({
        type: 'text',
        content: remaining
      })
    }
  }
  
  return parts.length > 0 ? parts : [{ type: 'text', content }]
}

// 复制代码
const copyCode = async (code) => {
  try {
    await navigator.clipboard.writeText(code)
    console.log('复制成功')
  } catch (err) {
    console.error('复制失败:', err)
  }
}
</script>

<template>
  <div class="chat-layout">
    <aside :class="['sidebar', { collapsed: isSidebarCollapsed }]">
      <div class="sidebar-header">
        <h2 v-show="!isSidebarCollapsed">接口AI助手</h2>
        <button class="sidebar-toggle-btn" @click="toggleSidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
      <div class="sidebar-content">
        <button class="new-chat-btn" @click="clearMessages">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <span v-show="!isSidebarCollapsed">新建对话</span>
        </button>
        <div class="chat-history">
        </div>
        <div v-if="!isSidebarCollapsed" class="auth-status-card">
          <div class="auth-user-name">{{ props.currentUser?.username || '当前用户' }}</div>
          <button class="auth-logout-btn" @click="logout">退出登录</button>
        </div>
      </div>
    </aside>
    
    <main class="main-content">
      <div class="messages-container" ref="messagesContainerRef">
          <div v-if="messages.length === 0" class="empty-state">
            <h1>接口AI助手</h1>
            <p>请输入厂商接口信息，AI 将为您完成全流程配置</p>
          </div>
          
          <div 
            v-for="(message, index) in messages" 
            :key="index"
            :class="['message', message.role]"
          >
            <div v-if="message.role === 'user'" class="user-text">{{ message.content }}</div>
            
            <template v-else>
              <div class="message-avatar">
                <div class="avatar ai-avatar">AI</div>
              </div>
              <div class="message-content">
                <div class="assistant-text">
                  <template v-for="(part, idx) in parseContent(message.content)" :key="idx">
                    <div v-if="part.type === 'text'" class="text-part" style="white-space: pre-wrap;">{{ part.content }}</div>
                    <div v-else class="code-block">
                      <div class="code-header">
                        <span class="language-tag">{{ part.language }}</span>
                        <button class="copy-btn" @click="copyCode(part.content)">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                            <path d="M8 4v12a2 2 0 002 2h8a2 2 0 002-2V7.242a2 2 0 00-.602-1.43L16.083 2.57A2 2 0 0014.685 2H10a2 2 0 00-2 2z" stroke="currentColor" stroke-width="2"/>
                            <path d="M16 18v2a2 2 0 01-2 2H6a2 2 0 01-2-2V9a2 2 0 012-2h2" stroke="currentColor" stroke-width="2"/>
                          </svg>
                          复制
                        </button>
                      </div>
                      <pre><code>{{ part.content }}</code></pre>
                    </div>
                  </template>
                </div>
              </div>
            </template>
          </div>
          
          <div v-if="isLoading" class="message assistant">
            <div class="message-avatar">
              <div class="avatar ai-avatar">AI</div>
            </div>
            <div class="message-content">
              <span class="loading-dots">思考中</span>
            </div>
          </div>
        </div>
        
        <div class="input-area">
          <div class="input-container">
            <textarea
              v-model="inputPrompt"
              :disabled="isLoading"
              placeholder="请输入厂商接口信息，例如：我要对接 HIS 建档接口..."
              @keydown.enter.exact.prevent="sendMessage"
              rows="1"
              ref="textareaRef"
            ></textarea>
            <button 
              @click="sendMessage" 
              :disabled="isLoading || !inputPrompt.trim()"
              class="send-btn"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
          <p class="input-hint">内容由 AI 生成，仅供参考</p>
        </div>
    </main>
  </div>
</template>

<style scoped>
/* 整体布局 */
.chat-layout {
  display: flex;
  width: 100%;
  height: 100%;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 左侧边栏 */
.sidebar {
  width: 280px;
  background: #1a1a1a;
  color: white;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #2a2a2a;
  transition: width 0.25s ease;
}

.sidebar.collapsed {
  width: 80px;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid #2a2a2a;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 78px;
  gap: 12px;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.sidebar-toggle-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid #3a3a3a;
  background: #2a2a2a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.sidebar-toggle-btn:hover {
  background: #3a3a3a;
}

.sidebar.collapsed .sidebar-toggle-btn svg {
  transform: rotate(180deg);
}

.sidebar-content {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.auth-status-card {
  border: 1px solid #3a3a3a;
  background: #232323;
  border-radius: 10px;
  padding: 12px;
  margin-top: auto;
}

.auth-user-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.auth-logout-btn {
  width: 100%;
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #545454;
  background: #2f2f2f;
  color: #fff;
  cursor: pointer;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #2a2a2a;
  color: white;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar.collapsed .new-chat-btn {
  justify-content: center;
  padding: 12px;
}

.new-chat-btn:hover {
  background: #3a3a3a;
}

.chat-history {
  margin-top: 16px;
}

/* 右侧主内容区 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
}

/* 消息区域 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 40px 20px;
}

/* 空状态 */
.empty-state {
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
  padding: 100px 20px;
}

.empty-state h1 {
  font-size: 32px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 16px 0;
}

.empty-state p {
  font-size: 16px;
  color: #666;
  margin: 0;
}

/* 消息 */
.message {
  width: 100%;
  margin: 0 0 32px 0;
  display: flex;
  gap: 16px;
  animation: fadeIn 0.3s ease;
}

.message.user {
  justify-content: flex-end;
  padding-right: 40px;
}

.message.assistant {
  justify-content: flex-start;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.user-avatar {
  background: #6b72ff;
  color: white;
}

.ai-avatar {
  background: #f0f0f0;
  color: #1a1a1a;
}

.message-content {
  flex: 1;
  max-width: 85%;
  padding-top: 8px;
}

.user-text,
.assistant-text {
  font-size: 15px;
  line-height: 1.7;
  color: #1a1a1a;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.user-text {
  background-color: #e3f2fd;
  padding: 16px 20px;
  border-radius: 16px;
  border-bottom-right-radius: 4px;
  max-width: 700px;
  line-height: 1.6;
  color: #1a1a1a;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.assistant-text {
  width: 100%;
  max-width: none;
}

/* 代码块样式 - 浅色主题 */
.code-block {
  margin: 16px 0;
  border-radius: 8px;
  overflow: hidden;
  background: #f6f8fa;
  border: 1px solid #d0d7de;
  max-width: 800px;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #e8ebed;
  border-bottom: 1px solid #d0d7de;
}

.language-tag {
  font-size: 12px;
  color: #57606a;
  text-transform: uppercase;
  font-weight: 600;
}

.copy-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: transparent;
  border: 1px solid #d0d7de;
  border-radius: 4px;
  color: #57606a;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: #f3f4f6;
  color: #1a1a1a;
  border-color: #8c959f;
}

.copy-btn svg {
  stroke: currentColor;
}

.code-block pre {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  background: #f6f8fa;
}

.code-block code {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #24292f;
  display: block;
}

.text-part {
  margin: 8px 0;
}

/* 输入区域 */
.input-area {
  border-top: 1px solid #e5e5e5;
  background: white;
  padding: 20px;
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  gap: 12px;
  align-items: center;
  background: #f7f8fa;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 12px 16px;
  transition: all 0.3s;
}

.input-container:focus-within {
  border-color: #6b72ff;
  background: white;
  box-shadow: 0 0 0 3px rgba(107, 114, 255, 0.1);
}

.input-container textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.6;
  padding: 6px 0;
  margin: 0;
  min-height: 24px;
  max-height: 200px;
  color: #1a1a1a;
}

.input-container textarea:focus {
  outline: none;
}

.input-container textarea::placeholder {
  color: #999;
}

.input-container textarea:disabled {
  opacity: 0.6;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: #6b72ff;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #5460e6;
}

.send-btn:disabled {
  background: #e0e0e0;
  cursor: not-allowed;
  opacity: 0.6;
}

.input-hint {
  text-align: center;
  color: #999;
  font-size: 13px;
  margin: 12px 0 0;
}

.loading-dots::after {
  content: '...';
  animation: dots 1.5s steps(4, end) infinite;
}

@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 滚动条美化 */
.messages-container::-webkit-scrollbar,
.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track,
.sidebar-content::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: #3a3a3a;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: #b0b0b0;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background: #4a4a4a;
}
</style>
