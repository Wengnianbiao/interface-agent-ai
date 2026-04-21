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
const sessionId = ref((typeof crypto !== 'undefined' && crypto.randomUUID)
  ? crypto.randomUUID()
  : `${Date.now()}-${Math.random().toString(36).slice(2)}`)

const generateSessionId = () =>
  (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`

const clearMessages = () => {
  messages.value = []
  activeSessionId.value = ''
  sessionId.value = generateSessionId()
}

const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

const logout = () => {
  messages.value = []
  inputPrompt.value = ''
  sessionRecords.value = []
  activeSessionId.value = ''
  sessionId.value = generateSessionId()
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
  let listType = 'ul'
  let i = 0

  const flushParagraph = () => {
    if (!paragraph.length) return
    blocks.push(`<p>${paragraph.map((line) => renderInlineMarkdown(line)).join('<br>')}</p>`)
    paragraph.length = 0
  }

  const flushList = () => {
    if (!listItems.length) return
    const tag = listType
    const items = listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')
    blocks.push(`<${tag}>${items}</${tag}>`)
    listItems.length = 0
    listType = 'ul'
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

    if (/^-{3,}$/.test(trimmed) || /^\*{3,}$/.test(trimmed)) {
      flushParagraph()
      flushList()
      blocks.push('<hr>')
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

    const orderedMatch = /^(\d+)[.)]\s+(.*)$/.exec(trimmed)
    if (orderedMatch) {
      flushParagraph()
      if (listItems.length && listType !== 'ol') flushList()
      listType = 'ol'
      listItems.push(orderedMatch[2])
      i += 1
      continue
    }

    if (/^([-*])\s+/.test(trimmed)) {
      flushParagraph()
      if (listItems.length && listType !== 'ul') flushList()
      listType = 'ul'
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

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainerRef.value) {
      messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight
    }
  })
}

const autoResizeTextarea = () => {
  const textarea = textareaRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
  }
}

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

const parseSSEEvents = (text) => {
  const events = []
  const blocks = text.split('\n\n')
  for (const block of blocks) {
    const trimmed = block.trim()
    if (!trimmed) continue
    let eventType = 'message'
    const dataLines = []
    const lines = trimmed.split('\n')
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        dataLines.push(line.slice(6))
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5))
      }
    }
    if (dataLines.length > 0) {
      events.push({ event: eventType, data: dataLines.join('\n') })
    }
  }
  return events
}

const PHASE_LABELS = {
  context: '分析需求',
  plan: '制定计划',
  resolve: '执行任务',
  tool: '调用工具',
  step_done: '步骤完成',
  answer: '生成回答',
}

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

  const ensureAssistantMessage = () => {
    if (aiMessageIndex === -1) {
      aiMessageIndex = messages.value.length
      messages.value.push({
        role: 'assistant',
        content: '',
        thinkingPhase: null,
        thinkingMessage: '',
        plan: null,
        toolCalls: [],
        errorMessage: null,
        doneData: null,
      })
      isLoading.value = false
    }
    return messages.value[aiMessageIndex]
  }

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

      const lastDoubleNewline = sseBuffer.lastIndexOf('\n\n')
      if (lastDoubleNewline === -1) continue

      const completePart = sseBuffer.slice(0, lastDoubleNewline + 2)
      sseBuffer = sseBuffer.slice(lastDoubleNewline + 2)

      const events = parseSSEEvents(completePart)
      for (const evt of events) {
        if (evt.event === 'thinking') {
          let parsed = {}
          try { parsed = JSON.parse(evt.data) } catch { parsed = { message: evt.data, phase: 'init' } }
          const msg = ensureAssistantMessage()
          msg.thinkingPhase = parsed.phase || 'init'
          msg.thinkingMessage = parsed.message || ''

          if (parsed.phase === 'resolve' && parsed.stepNo && msg.plan) {
            const steps = msg.plan.resolveSteps || []
            steps.forEach((s) => {
              if (s.stepNo === parsed.stepNo) s.status = 'running'
            })
          }
          if (parsed.phase === 'step_done' && parsed.stepNo && msg.plan) {
            const steps = msg.plan.resolveSteps || []
            steps.forEach((s) => {
              if (s.stepNo === parsed.stepNo) s.status = 'done'
            })
          }
        } else if (evt.event === 'plan') {
          let planData = null
          try { planData = JSON.parse(evt.data) } catch { /* ignore */ }
          const msg = ensureAssistantMessage()
          if (planData && planData.resolveSteps) {
            planData.resolveSteps = planData.resolveSteps.map((s) => ({ ...s, status: 'pending' }))
          }
          msg.plan = planData
          msg.thinkingPhase = null
        } else if (evt.event === 'content') {
          contentText += evt.data
          const msg = ensureAssistantMessage()
          msg.content = contentText
          msg.thinkingPhase = null
        } else if (evt.event === 'tool_call') {
          let toolData = null
          try { toolData = JSON.parse(evt.data) } catch { /* ignore */ }
          const msg = ensureAssistantMessage()
          if (toolData) {
            msg.toolCalls.push({
              tool: toolData.tool || 'unknown',
              payload: toolData.payload || {},
              result: toolData.result || {},
              collapsed: true,
            })
          }
          msg.thinkingPhase = null
        } else if (evt.event === 'error') {
          let errMsg = ''
          try { errMsg = JSON.parse(evt.data).message } catch { errMsg = evt.data }
          const msg = ensureAssistantMessage()
          msg.errorMessage = errMsg
          msg.thinkingPhase = null
        } else if (evt.event === 'done') {
          let doneData = {}
          try { doneData = JSON.parse(evt.data) } catch { /* ignore */ }
          const msg = ensureAssistantMessage()
          msg.doneData = doneData
          msg.thinkingPhase = null
          if (msg.plan && msg.plan.resolveSteps) {
            msg.plan.resolveSteps.forEach((s) => {
              if (s.status !== 'done') s.status = 'done'
            })
          }
        }
      }
      scrollToBottom()
    }
  } catch (error) {
    console.error('请求失败:', error)
    const msg = ensureAssistantMessage()
    msg.errorMessage = `请求失败：${error.message}`
  } finally {
    isLoading.value = false
    await fetchSessionRecords()
  }
}

const parseContent = (content) => {
  const parts = []
  const regex = /```(\w+)?\n([\s\S]*?)```/g
  let lastIndex = 0
  let match
  
  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.substring(lastIndex, match.index),
        html: renderMarkdownText(content.substring(lastIndex, match.index))
      })
    }
    parts.push({
      type: 'code',
      language: match[1] || 'text',
      content: match[2],
      completed: true
    })
    lastIndex = regex.lastIndex
  }
  
  const remaining = content.substring(lastIndex)
  if (remaining) {
    const incompleteMatch = /```(\w+)?\n([\s\S]*)$/.exec(remaining)
    if (incompleteMatch) {
      const beforeCode = remaining.substring(0, incompleteMatch.index)
      if (beforeCode) {
        parts.push({
          type: 'text',
          content: beforeCode,
          html: renderMarkdownText(beforeCode)
        })
      }
      parts.push({
        type: 'code',
        language: incompleteMatch[1] || 'text',
        content: incompleteMatch[2],
        completed: false
      })
    } else {
      parts.push({
        type: 'text',
        content: remaining,
        html: renderMarkdownText(remaining)
      })
    }
  }
  
  return parts.length > 0 ? parts : [{ type: 'text', content, html: renderMarkdownText(content) }]
}

const copyCode = async (code) => {
  try {
    await navigator.clipboard.writeText(code)
  } catch (err) {
    console.error('复制失败:', err)
  }
}

const toggleToolCollapse = (toolCall) => {
  toolCall.collapsed = !toolCall.collapsed
}

const routeTagClass = (route) => {
  const map = {
    '自动化配置': 'tag-auto',
    '规则问答': 'tag-qa',
    '可行性评估': 'tag-eval',
    'SPI扩展': 'tag-spi',
    '配置生成': 'tag-config',
  }
  return map[route] || 'tag-default'
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
            <div class="empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="#e8eaff"/>
                <path d="M8 14s1.5 2 4 2 4-2 4-2" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="9" cy="10" r="1.2" fill="#6366f1"/>
                <circle cx="15" cy="10" r="1.2" fill="#6366f1"/>
              </svg>
            </div>
            <h1>接口AI助手</h1>
            <p>请输入厂商接口信息，AI 将为您完成全流程配置</p>
          </div>
          
          <div 
            v-for="(message, index) in messages" 
            :key="index"
            :class="['message', message.role]"
          >
            <!-- 用户消息 -->
            <div v-if="message.role === 'user'" class="user-text">{{ message.content }}</div>
            
            <!-- AI 消息 -->
            <template v-else>
              <div class="message-avatar">
                <div class="avatar ai-avatar">AI</div>
              </div>
              <div class="message-content">

                <!-- Thinking 状态指示器 -->
                <div v-if="message.thinkingPhase" class="thinking-card">
                  <div class="thinking-pulse"></div>
                  <div class="thinking-body">
                    <span class="thinking-label">{{ message.thinkingMessage }}</span>
                  </div>
                </div>

                <!-- Plan 执行计划卡片 -->
                <div v-if="message.plan" class="plan-card">
                  <div class="plan-card-header">
                    <div class="plan-card-icon">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" stroke-width="2"/>
                      </svg>
                    </div>
                    <div class="plan-card-titles">
                      <div class="plan-card-title">执行计划</div>
                      <div class="plan-card-subtitle">
                        <span :class="['route-tag', routeTagClass(message.plan.taskRoute)]">{{ message.plan.taskRoute || '默认路线' }}</span>
                        <span class="plan-scenario">{{ message.plan.scenarioName || '通用场景' }}</span>
                      </div>
                    </div>
                  </div>
                  <div v-if="message.plan.objective" class="plan-card-objective">{{ message.plan.objective }}</div>
                  <div class="plan-steps">
                    <div 
                      v-for="step in message.plan.resolveSteps || []" 
                      :key="step.stepNo" 
                      :class="['plan-step', `step-${step.status || 'pending'}`]"
                    >
                      <div :class="['plan-step-status', `status-${step.status || 'pending'}`]">
                        <svg v-if="!step.status || step.status === 'pending'" width="14" height="14" viewBox="0 0 24 24" fill="none">
                          <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" stroke-dasharray="4 3"/>
                        </svg>
                        <div v-else-if="step.status === 'running'" class="step-spinner"></div>
                        <svg v-else-if="step.status === 'done'" width="14" height="14" viewBox="0 0 24 24" fill="none">
                          <circle cx="12" cy="12" r="9" fill="#10b981" stroke="#10b981" stroke-width="2"/>
                          <path d="M8 12l2.5 3L16 9" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                      </div>
                      <div class="plan-step-body">
                        <div class="plan-step-name">{{ step.stepName }}</div>
                        <div class="plan-step-meta">{{ step.objective }}</div>
                      </div>
                    </div>
                  </div>
                  <!-- 进度条 -->
                  <div v-if="message.plan.resolveSteps?.length" class="plan-progress">
                    <div 
                      class="plan-progress-bar" 
                      :style="{ width: Math.round((message.plan.resolveSteps.filter(s => s.status === 'done').length / message.plan.resolveSteps.length) * 100) + '%' }"
                    ></div>
                  </div>
                </div>

                <!-- 错误提示卡片 -->
                <div v-if="message.errorMessage" class="error-card">
                  <div class="error-card-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M12 9v4m0 4h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                    </svg>
                  </div>
                  <div class="error-card-body">
                    <div class="error-card-title">处理出现问题</div>
                    <div class="error-card-msg">{{ message.errorMessage }}</div>
                  </div>
                </div>

                <!-- 正文内容 -->
                <div v-if="message.content" class="assistant-text">
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

                <!-- 工具调用卡片 -->
                <div v-for="(tc, tcIdx) in (message.toolCalls || [])" :key="tcIdx" class="tool-card">
                  <div class="tool-card-header" @click="toggleToolCollapse(tc)">
                    <div class="tool-card-icon">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                      </svg>
                    </div>
                    <span class="tool-card-name">{{ tc.tool.toUpperCase() }}</span>
                    <span class="tool-card-status">已完成</span>
                    <svg :class="['tool-card-chevron', { expanded: !tc.collapsed }]" width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </div>
                  <div v-if="!tc.collapsed" class="tool-card-body">
                    <div class="tool-section">
                      <div class="tool-section-label">调用参数</div>
                      <pre class="tool-json"><code>{{ JSON.stringify(tc.payload, null, 2) }}</code></pre>
                    </div>
                    <div class="tool-section">
                      <div class="tool-section-label">执行结果</div>
                      <pre class="tool-json"><code>{{ JSON.stringify(tc.result, null, 2) }}</code></pre>
                    </div>
                  </div>
                </div>

                <!-- Done 摘要栏 -->
                <div v-if="message.doneData && message.content" class="done-bar">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="9" fill="#10b981" stroke="#10b981" stroke-width="2"/>
                    <path d="M8 12l2.5 3L16 9" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span>任务完成</span>
                  <span v-if="message.doneData.taskRoute" class="done-route">{{ message.doneData.taskRoute }}</span>
                </div>

              </div>
            </template>
          </div>
          
          <!-- 全局 Loading -->
          <div v-if="isLoading" class="message assistant">
            <div class="message-avatar">
              <div class="avatar ai-avatar">AI</div>
            </div>
            <div class="message-content">
              <div class="loading-skeleton">
                <div class="skeleton-line long"></div>
                <div class="skeleton-line medium"></div>
                <div class="skeleton-line short"></div>
              </div>
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
/* ============= 布局 ============= */
.chat-layout {
  display: flex;
  width: 100%;
  height: 100%;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* ============= 侧边栏 ============= */
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

/* ============= 主内容区 ============= */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 40px 20px;
}

/* ============= 空状态 ============= */
.empty-state {
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
  padding: 100px 20px;
}

.empty-icon {
  margin-bottom: 20px;
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

/* ============= 消息 ============= */
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

.ai-avatar {
  background: linear-gradient(135deg, #e8eaff, #d4d8ff);
  color: #4f46e5;
}

.message-content {
  flex: 1;
  max-width: 85%;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-text {
  background-color: #e3f2fd;
  padding: 16px 20px;
  border-radius: 16px;
  border-bottom-right-radius: 4px;
  max-width: 700px;
  font-size: 15px;
  line-height: 1.6;
  color: #1a1a1a;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.assistant-text {
  width: 100%;
  font-size: 15px;
  line-height: 1.7;
  color: #1a1a1a;
  word-wrap: break-word;
}

/* ============= Thinking 卡片 ============= */
.thinking-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: linear-gradient(135deg, #f0f1ff, #eef0ff);
  border: 1px solid #d4d8ff;
  border-radius: 10px;
  animation: fadeIn 0.3s ease;
  font-size: 13px;
  max-width: 420px;
}

.thinking-pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #6366f1;
  flex-shrink: 0;
  animation: pulse 1.5s ease-in-out infinite;
}

.thinking-body {
  flex: 1;
}

.thinking-label {
  font-size: 14px;
  font-weight: 500;
  color: #4338ca;
}

/* ============= Plan 卡片 ============= */
.plan-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 420px;
}

.plan-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plan-card-icon {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: linear-gradient(135deg, #6366f1, #818cf8);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.plan-card-icon svg { width: 14px; height: 14px; }

.plan-card-titles {
  flex: 1;
}

.plan-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.plan-card-subtitle {
  font-size: 11px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 1px;
}

.route-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.tag-auto { background: #dbeafe; color: #1d4ed8; }
.tag-qa { background: #f0fdf4; color: #15803d; }
.tag-eval { background: #fef3c7; color: #a16207; }
.tag-spi { background: #fce7f3; color: #be185d; }
.tag-config { background: #e0e7ff; color: #4338ca; }
.tag-default { background: #f1f5f9; color: #475569; }

.plan-scenario {
  color: #94a3b8;
}

.plan-card-objective {
  color: #475569;
  font-size: 12px;
  line-height: 1.4;
  padding: 0 2px;
}

.plan-steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.plan-step {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 6px 10px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.plan-step.step-running {
  border-color: #818cf8;
  background: #fafaff;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1);
}

.plan-step.step-done {
  border-color: #86efac;
  background: #f0fdf4;
}

.plan-step-status {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.plan-step-status svg { width: 14px; height: 14px; }

.status-pending { color: #cbd5e1; }
.status-running { color: #6366f1; }
.status-done { color: #10b981; }

.step-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #e0e7ff;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.plan-step-body {
  flex: 1;
  min-width: 0;
}

.plan-step-name {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.plan-step-meta {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 1px;
  line-height: 1.4;
}

.plan-step-no {
  font-size: 10px;
  color: #cbd5e1;
  font-weight: 500;
  flex-shrink: 0;
}

.plan-progress {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
}

.plan-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #10b981);
  border-radius: 2px;
  transition: width 0.5s ease;
}

/* ============= Error 卡片 ============= */
.error-card {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
}

.error-card-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #fee2e2;
  color: #dc2626;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.error-card-body {
  flex: 1;
}

.error-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #991b1b;
  margin-bottom: 4px;
}

.error-card-msg {
  font-size: 13px;
  color: #b91c1c;
  line-height: 1.5;
}

/* ============= Tool Call 卡片 ============= */
.tool-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: #f8fafc;
}

.tool-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.tool-card-header:hover {
  background: #f1f5f9;
}

.tool-card-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #e0e7ff;
  color: #4338ca;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tool-card-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.tool-card-status {
  font-size: 12px;
  color: #10b981;
  font-weight: 500;
  margin-left: auto;
}

.tool-card-chevron {
  color: #94a3b8;
  transition: transform 0.2s;
  flex-shrink: 0;
}

.tool-card-chevron.expanded {
  transform: rotate(180deg);
}

.tool-card-body {
  border-top: 1px solid #e2e8f0;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: slideDown 0.2s ease;
}

.tool-section-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.tool-json {
  margin: 0;
  padding: 12px;
  background: #f1f5f9;
  border-radius: 8px;
  overflow-x: auto;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #334155;
}

/* ============= Done 摘要栏 ============= */
.done-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 13px;
  color: #15803d;
  font-weight: 500;
}

.done-route {
  margin-left: auto;
  font-size: 12px;
  padding: 2px 8px;
  background: #dcfce7;
  border-radius: 4px;
  color: #166534;
}

/* ============= Loading 骨架屏 ============= */
.loading-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px 0;
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-line.long { width: 80%; }
.skeleton-line.medium { width: 60%; }
.skeleton-line.short { width: 40%; }

/* ============= 代码块 ============= */
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

/* ============= Markdown 文本 ============= */
.text-part {
  margin: 8px 0;
  line-height: 1.8;
  color: #1a1a1a;
}

.text-part :deep(p) { margin: 0 0 10px; }
.text-part :deep(h1) { margin: 18px 0 10px; color: #0f172a; font-weight: 700; font-size: 20px; }
.text-part :deep(h2) { margin: 16px 0 8px; color: #0f172a; font-weight: 700; font-size: 17px; }
.text-part :deep(h3) { margin: 14px 0 8px; color: #0f172a; font-weight: 600; font-size: 15px; }
.text-part :deep(h4),
.text-part :deep(h5),
.text-part :deep(h6) { margin: 12px 0 6px; color: #0f172a; font-weight: 600; font-size: 14px; }
.text-part :deep(ul),
.text-part :deep(ol) { margin: 8px 0 12px 22px; padding: 0; }
.text-part :deep(li) { margin: 4px 0; }
.text-part :deep(hr) { border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }
.text-part :deep(strong) { font-weight: 700; }
.text-part :deep(em) { font-style: italic; }
.text-part :deep(a) { color: #4f46e5; text-decoration: none; }
.text-part :deep(a:hover) { text-decoration: underline; }
.text-part :deep(code) {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  background: #eef2ff;
  color: #3730a3;
  padding: 2px 6px;
  border-radius: 4px;
}
.text-part :deep(.markdown-table-wrapper) { width: 100%; overflow-x: auto; margin: 10px 0 14px; }
.text-part :deep(table) { width: 100%; border-collapse: collapse; border: 1px solid #dfe3ea; font-size: 14px; background: #fff; }
.text-part :deep(th),
.text-part :deep(td) { border: 1px solid #dfe3ea; padding: 8px 10px; text-align: left; vertical-align: top; }
.text-part :deep(th) { background: #f8fafc; color: #0f172a; font-weight: 600; }

/* ============= 输入区域 ============= */
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

.input-container textarea:focus { outline: none; }
.input-container textarea::placeholder { color: #999; }
.input-container textarea:disabled { opacity: 0.6; }

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

.send-btn:hover:not(:disabled) { background: #5460e6; }
.send-btn:disabled { background: #e0e0e0; cursor: not-allowed; opacity: 0.6; }

.input-hint {
  text-align: center;
  color: #999;
  font-size: 13px;
  margin: 12px 0 0;
}

/* ============= 动画 ============= */
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideDown {
  from { opacity: 0; max-height: 0; }
  to { opacity: 1; max-height: 600px; }
}

/* ============= 滚动条 ============= */
.messages-container::-webkit-scrollbar,
.sidebar-content::-webkit-scrollbar { width: 4px; }
.messages-container::-webkit-scrollbar-track,
.sidebar-content::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.04); border-radius: 10px; }
.sidebar-content::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.06); }
.chat-history-list::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.02); }
.messages-container::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.18); border-radius: 10px; }
.sidebar-content::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.18); border-radius: 10px; }
.chat-history-list::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.12); }
.messages-container::-webkit-scrollbar-thumb:hover { background: rgba(0, 0, 0, 0.32); }
.sidebar-content::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.32); }
.chat-history-list::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
</style>
