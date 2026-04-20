<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'

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
const sessionRecords = ref([])
const isLoadingSessions = ref(false)
const sessionLoadError = ref('')
const activeSessionId = ref('')
const planStartMarker = '<<<PLAN_JSON>>>'
const planEndMarker = '<<<END_PLAN_JSON>>>'
const sessionId = ref((typeof crypto !== 'undefined' && crypto.randomUUID)
  ? crypto.randomUUID()
  : `${Date.now()}-${Math.random().toString(36).slice(2)}`)

// 清空消息
const clearMessages = () => {
  messages.value = []
  activeSessionId.value = ''
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
  sessionRecords.value = []
  activeSessionId.value = ''
  sessionId.value = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`
  emit('logout')
}

const authHeaders = () => ({
  ...(props.accessToken ? { Authorization: `Bearer ${props.accessToken}` } : {})
})

const fetchSessionRecords = async () => {
  if (!props.accessToken) return
  isLoadingSessions.value = true
  sessionLoadError.value = ''
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
      headers: authHeaders()
    })
    if (!response.ok) {
      sessionLoadError.value = response.status === 404
        ? '会话接口未就绪，请重启后端'
        : '会话记录加载失败'
      return
    }
    const payload = await response.json()
    sessionRecords.value = Array.isArray(payload?.sessions) ? payload.sessions : []
  } catch (_error) {
    sessionRecords.value = []
    sessionLoadError.value = '会话记录加载失败'
  } finally {
    isLoadingSessions.value = false
  }
}

const loadSessionMessages = async (targetSessionId) => {
  if (!targetSessionId || !props.accessToken) return
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${encodeURIComponent(targetSessionId)}/messages`, {
      headers: authHeaders()
    })
    if (!response.ok) return
    const payload = await response.json()
    const list = Array.isArray(payload?.messages) ? payload.messages : []
    messages.value = list.map((item) => ({
      role: item.role,
      content: item.content
    }))
    sessionId.value = targetSessionId
    activeSessionId.value = targetSessionId
    scrollToBottom()
  } catch (_error) {
  }
}

const selectSession = async (targetSessionId) => {
  if (!targetSessionId || isLoading.value) return
  await loadSessionMessages(targetSessionId)
}

const formatSessionMeta = (record) => {
  const qa = Number(record?.qaCount || 0)
  return `${qa}轮对话`
}

const extractPlanPayload = (text) => {
  const start = text.indexOf(planStartMarker)
  const end = text.indexOf(planEndMarker)
  if (start === -1 || end === -1 || end <= start) {
    return { cleanText: text, plan: null }
  }
  const jsonText = text.slice(start + planStartMarker.length, end).trim()
  let plan = null
  try {
    plan = JSON.parse(jsonText)
  } catch (_error) {
    plan = null
  }
  const cleaned = `${text.slice(0, start)}${text.slice(end + planEndMarker.length)}`.trim()
  return { cleanText: cleaned, plan }
}

const escapeHtml = (value) => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;')

const renderInlineMarkdown = (source) => {
  const escaped = escapeHtml(source)
  return escaped
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
}

const isTableDivider = (line) => {
  const trimmed = line.trim()
  if (!trimmed.includes('|')) return false
  const cells = trimmed
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
  if (cells.length === 0) return false
  return cells.every((cell) => /^:?-{3,}:?$/.test(cell))
}

const normalizeTableCells = (line) => line
  .trim()
  .replace(/^\|/, '')
  .replace(/\|$/, '')
  .split('|')
  .map((cell) => cell.trim())

const renderMarkdownText = (content) => {
  const lines = content.replaceAll('\r\n', '\n').split('\n')
  const blocks = []
  const paragraph = []
  const listItems = []
  let i = 0

  const flushParagraph = () => {
    if (!paragraph.length) return
    blocks.push(`<p>${paragraph.map((line) => renderInlineMarkdown(line)).join('<br>')}</p>`)
    paragraph.length = 0
  }

  const flushList = () => {
    if (!listItems.length) return
    const items = listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')
    blocks.push(`<ul>${items}</ul>`)
    listItems.length = 0
  }

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()
    if (!trimmed) {
      flushParagraph()
      flushList()
      i += 1
      continue
    }

    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(trimmed)
    if (headingMatch) {
      flushParagraph()
      flushList()
      const level = headingMatch[1].length
      blocks.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`)
      i += 1
      continue
    }

    if (/^([-*])\s+/.test(trimmed)) {
      flushParagraph()
      listItems.push(trimmed.replace(/^([-*])\s+/, ''))
      i += 1
      continue
    }

    if (trimmed.includes('|') && i + 1 < lines.length && isTableDivider(lines[i + 1])) {
      flushParagraph()
      flushList()
      const headerCells = normalizeTableCells(trimmed)
      const bodyRows = []
      i += 2
      while (i < lines.length && lines[i].trim().includes('|') && lines[i].trim()) {
        bodyRows.push(normalizeTableCells(lines[i]))
        i += 1
      }
      const head = `<thead><tr>${headerCells.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join('')}</tr></thead>`
      const body = bodyRows.length
        ? `<tbody>${bodyRows.map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join('')}</tr>`).join('')}</tbody>`
        : ''
      blocks.push(`<div class="markdown-table-wrapper"><table>${head}${body}</table></div>`)
      continue
    }

    paragraph.push(trimmed)
    i += 1
  }

  flushParagraph()
  flushList()
  return blocks.join('')
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

watch(() => props.accessToken, async (newToken) => {
  if (newToken) {
    await fetchSessionRecords()
  } else {
    sessionRecords.value = []
    sessionLoadError.value = ''
  }
})

onMounted(async () => {
  await fetchSessionRecords()
})

// SSE事件解析器
const parseSSEEvents = (text) => {
  const events = []
  // 按双换行分割事件块
  const blocks = text.split('\n\n')
  for (const block of blocks) {
    const trimmed = block.trim()
    if (!trimmed) continue
    let eventType = 'message'
    let data = ''
    const lines = trimmed.split('\n')
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        data = line.slice(6)
      }
    }
    if (data) {
      events.push({ event: eventType, data })
    }
  }
  return events
}

// 发送消息
const sendMessage = async () => {
  if (!inputPrompt.value.trim() || isLoading.value) return

  const userMessage = inputPrompt.value.trim()
  let aiMessageIndex = -1

  messages.value.push({ role: 'user', content: userMessage })
  scrollToBottom()

  inputPrompt.value = ''
  nextTick(() => {
    if (textareaRef.value) textareaRef.value.style.height = 'auto'
  })

  isLoading.value = true

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ prompt: userMessage, sessionId: sessionId.value })
    })

    const responseSessionId = response.headers.get('X-Session-Id')
    if (responseSessionId) {
      sessionId.value = responseSessionId
      activeSessionId.value = responseSessionId
    }

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let sseBuffer = ''
    let contentText = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      sseBuffer += decoder.decode(value, { stream: true })

      // 尝试解析完整的SSE事件
      const lastDoubleNewline = sseBuffer.lastIndexOf('\n\n')
      if (lastDoubleNewline === -1) continue

      const completePart = sseBuffer.slice(0, lastDoubleNewline + 2)
      sseBuffer = sseBuffer.slice(lastDoubleNewline + 2)

      const events = parseSSEEvents(completePart)
      for (const evt of events) {
        if (evt.event === 'thinking') {
          // 阶段状态 - 创建或更新AI消息
          let msg = ''
          try { msg = JSON.parse(evt.data).message } catch { msg = evt.data }
          if (aiMessageIndex === -1) {
            aiMessageIndex = messages.value.length
            messages.value.push({ role: 'assistant', content: '', thinking: msg, plan: null })
            isLoading.value = false
          } else {
            messages.value[aiMessageIndex].thinking = msg
          }
        } else if (evt.event === 'plan') {
          let planData = null
          try { planData = JSON.parse(evt.data) } catch { /* ignore */ }
          if (aiMessageIndex === -1) {
            aiMessageIndex = messages.value.length
            messages.value.push({ role: 'assistant', content: '', plan: planData })
            isLoading.value = false
          } else {
            messages.value[aiMessageIndex].plan = planData
          }
        } else if (evt.event === 'content') {
          contentText += evt.data
          if (aiMessageIndex === -1) {
            aiMessageIndex = messages.value.length
            messages.value.push({ role: 'assistant', content: contentText, plan: null })
            isLoading.value = false
          } else {
            messages.value[aiMessageIndex].content = contentText
            messages.value[aiMessageIndex].thinking = null
          }
        } else if (evt.event === 'tool_call') {
          let toolData = null
          try { toolData = JSON.parse(evt.data) } catch { /* ignore */ }
          if (aiMessageIndex !== -1 && toolData) {
            const resultJson = JSON.stringify(toolData.result || {}, null, 2)
            contentText += `\n\n\u3010MCP\u6267\u884c\u7ed3\u679c\u3011\n\`\`\`json\n${resultJson}\n\`\`\``
            messages.value[aiMessageIndex].content = contentText
          }
        } else if (evt.event === 'error') {
          let errMsg = ''
          try { errMsg = JSON.parse(evt.data).message } catch { errMsg = evt.data }
          if (aiMessageIndex === -1) {
            aiMessageIndex = messages.value.length
            messages.value.push({ role: 'assistant', content: `\u274c ${errMsg}` })
            isLoading.value = false
          } else {
            messages.value[aiMessageIndex].content += `\n\n\u274c ${errMsg}`
          }
        }
        // done event - 不需要额外处理
      }
      scrollToBottom()
    }
  } catch (error) {
    console.error('请求失败:', error)
    if (aiMessageIndex === -1) {
      messages.value.push({ role: 'assistant', content: `\u274c \u8bf7\u6c42\u5931\u8d25\uff1a${error.message}` })
    } else {
      messages.value[aiMessageIndex].content = `\u274c \u8bf7\u6c42\u5931\u8d25\uff1a${error.message}`
    }
  } finally {
    isLoading.value = false
    await fetchSessionRecords()
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
        content: content.substring(lastIndex, match.index),
        html: renderMarkdownText(content.substring(lastIndex, match.index))
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
          content: beforeCode,
          html: renderMarkdownText(beforeCode)
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
        content: remaining,
        html: renderMarkdownText(remaining)
      })
    }
  }
  
  return parts.length > 0 ? parts : [{ type: 'text', content, html: renderMarkdownText(content) }]
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
        <div class="sidebar-top">
          <button class="new-chat-btn" @click="clearMessages">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span v-show="!isSidebarCollapsed">新建对话</span>
          </button>
        </div>
        <div v-show="!isSidebarCollapsed" class="chat-history">
          <div class="chat-history-title">会话记录</div>
          <div v-if="isLoadingSessions" class="chat-history-empty">加载中...</div>
          <div v-else-if="sessionLoadError" class="chat-history-empty">{{ sessionLoadError }}</div>
          <div v-else-if="sessionRecords.length === 0" class="chat-history-empty">暂无历史会话</div>
          <div class="chat-history-list">
            <button
              v-for="record in sessionRecords"
              :key="record.sessionId"
              class="history-item"
              :class="{ active: activeSessionId === record.sessionId }"
              @click="selectSession(record.sessionId)"
            >
              <div class="history-item-title">{{ record.title }}</div>
              <div class="history-item-meta">{{ formatSessionMeta(record) }}</div>
            </button>
          </div>
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
                <div v-if="message.thinking" class="thinking-status">
                  <span class="thinking-indicator">{{ message.thinking }}</span>
                </div>
                <div v-if="message.plan" class="plan-card">
                  <div class="plan-card-title">执行计划</div>
                  <div class="plan-card-subtitle">
                    <span>{{ message.plan.scenarioName || '通用场景' }}</span>
                    <span class="plan-card-dot">•</span>
                    <span>{{ message.plan.taskRoute || '默认路线' }}</span>
                  </div>
                  <div v-if="message.plan.objective" class="plan-card-objective">{{ message.plan.objective }}</div>
                  <div class="plan-steps">
                    <div v-for="step in message.plan.resolveSteps || []" :key="step.stepNo" class="plan-step">
                      <div class="plan-step-index">{{ step.stepNo }}</div>
                      <div class="plan-step-body">
                        <div class="plan-step-name">{{ step.stepName }}</div>
                        <div class="plan-step-meta">{{ step.objective }}</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="assistant-text">
                  <template v-for="(part, idx) in parseContent(message.content)" :key="idx">
                    <div v-if="part.type === 'text'" class="text-part" v-html="part.html"></div>
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
  overflow: hidden;
  gap: 12px;
}

.sidebar-top {
  flex-shrink: 0;
}

.auth-status-card {
  border: 1px solid #3a3a3a;
  background: #232323;
  border-radius: 10px;
  padding: 12px;
  flex-shrink: 0;
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
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.chat-history-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  padding-right: 4px;
}

.chat-history-title {
  font-size: 12px;
  color: #a9a9a9;
  margin: 2px 4px 4px;
}

.chat-history-empty {
  color: #8f8f8f;
  font-size: 12px;
  padding: 8px 10px;
}

.history-item {
  width: 100%;
  text-align: left;
  border: 1px solid #333;
  background: #252525;
  color: #fff;
  border-radius: 8px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-item:hover {
  background: #2f2f2f;
}

.history-item.active {
  border-color: #6366f1;
  background: #2a2f52;
}

.history-item-title {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-item-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #b8b8b8;
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

.plan-card {
  width: 100%;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.thinking-status {
  padding: 8px 0;
  margin-bottom: 8px;
}

.thinking-indicator {
  color: #6366f1;
  font-size: 14px;
  font-weight: 500;
}

.thinking-indicator::after {
  content: '...';
  animation: dots 1.5s steps(4, end) infinite;
}

.plan-card-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.plan-card-subtitle {
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.plan-card-dot {
  font-size: 10px;
}

.plan-card-objective {
  color: #334155;
  font-size: 13px;
}

.plan-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-step {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
}

.plan-step-index {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: #6366f1;
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.plan-step-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.plan-step-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.plan-step-meta {
  font-size: 12px;
  color: #64748b;
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
  line-height: 1.8;
  color: #1a1a1a;
}

.text-part :deep(p) {
  margin: 0 0 10px;
}

.text-part :deep(h1),
.text-part :deep(h2),
.text-part :deep(h3),
.text-part :deep(h4),
.text-part :deep(h5),
.text-part :deep(h6) {
  margin: 16px 0 10px;
  color: #0f172a;
  font-weight: 600;
}

.text-part :deep(ul) {
  margin: 8px 0 12px 22px;
  padding: 0;
}

.text-part :deep(li) {
  margin: 4px 0;
}

.text-part :deep(strong) {
  font-weight: 700;
}

.text-part :deep(em) {
  font-style: italic;
}

.text-part :deep(a) {
  color: #4f46e5;
  text-decoration: none;
}

.text-part :deep(a:hover) {
  text-decoration: underline;
}

.text-part :deep(code) {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  background: #eef2ff;
  color: #3730a3;
  padding: 2px 6px;
  border-radius: 4px;
}

.text-part :deep(.markdown-table-wrapper) {
  width: 100%;
  overflow-x: auto;
  margin: 10px 0 14px;
}

.text-part :deep(table) {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid #dfe3ea;
  font-size: 14px;
  background: #fff;
}

.text-part :deep(th),
.text-part :deep(td) {
  border: 1px solid #dfe3ea;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.text-part :deep(th) {
  background: #f8fafc;
  color: #0f172a;
  font-weight: 600;
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
  width: 4px;
}

.messages-container::-webkit-scrollbar-track,
.sidebar-content::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.04);
  border-radius: 10px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.06);
}

.chat-history-list::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
}

.messages-container::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.18);
  border-radius: 10px;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.18);
  border-radius: 10px;
}

.chat-history-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.32);
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.32);
}

.chat-history-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
