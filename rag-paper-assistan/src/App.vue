<script setup lang="ts">
import { computed, ref } from 'vue'

interface HistoryItem {
  id: number
  title: string
  time: string
  preview: string
}

const historyOpen = ref(false)
const inputValue = ref('')

const historyItems = ref<HistoryItem[]>([
  {
    id: 1,
    title: 'RAG 论文综述初稿',
    time: '今天 14:20',
    preview: '整理检索增强生成在论文助手中的应用脉络',
  },
  {
    id: 2,
    title: '多模态 Agent 调研',
    time: '昨天 20:48',
    preview: '聚焦视觉理解、工具调用和科研辅助场景',
  },
  {
    id: 3,
    title: '引用规范修订',
    time: '04-30 09:16',
    preview: '对 GB/T 7714 和 APA 的输出格式进行比对',
  },
])

const quickPrompts = [
  '帮我梳理某个研究方向的代表性工作',
  '基于本地论文生成一版文献综述提纲',
  '补充 2024 年之后的最新研究并说明趋势',
  '检查参考文献格式是否符合论文规范',
]

const canSend = computed(() => inputValue.value.trim().length > 0)

function toggleHistory() {
  historyOpen.value = !historyOpen.value
}

function usePrompt(prompt: string) {
  inputValue.value = prompt
}

function sendMessage() {
  if (!canSend.value) {
    return
  }

  // 当前阶段仅作为起始页原型，后续可接入真实对话流。
  inputValue.value = ''
}
</script>

<template>
  <div class="landing-shell">
    <aside class="history-drawer" :class="{ 'is-open': historyOpen }">
      <div class="drawer-header">
        <div>
          <p class="drawer-kicker">History</p>
          <h2>历史记录</h2>
        </div>
        <button class="ghost-button" type="button" @click="toggleHistory">收起</button>
      </div>

      <div class="history-list">
        <button
          v-for="item in historyItems"
          :key="item.id"
          class="history-item"
          type="button"
        >
          <span class="history-time">{{ item.time }}</span>
          <strong>{{ item.title }}</strong>
          <p>{{ item.preview }}</p>
        </button>
      </div>
    </aside>

    <main class="chat-stage" :class="{ 'with-history': historyOpen }">
      <header class="topbar">
        <button class="history-toggle" type="button" @click="toggleHistory">
          <span class="history-toggle__icon" />
          <span>历史记录</span>
        </button>

        <div class="brand-mark">
          <span class="brand-mark__dot" />
          <span>Paper Assistant</span>
        </div>
      </header>

      <section class="hero-panel">
        <div class="hero-copy">
          <p class="hero-kicker">RAG Paper Assistant</p>
          <h1>从文献收集到综述撰写，先从一段对话开始。</h1>
          <p class="hero-description">
            输入你的研究方向、问题或修改要求，后续这里会接上本地知识库、外部检索和论文综述生成能力。
          </p>
        </div>

        <div class="prompt-grid">
          <button
            v-for="prompt in quickPrompts"
            :key="prompt"
            class="prompt-card"
            type="button"
            @click="usePrompt(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
      </section>

      <section class="chat-card">
        <div class="chat-placeholder">
          <div class="assistant-badge">AI</div>
          <div class="chat-placeholder__body">
            <h3>欢迎来到论文助手</h3>
            <p>
              这里现在是起始页原型，后续你可以把对话输入直接接到论文检索、知识库构建和综述生成流程里。
            </p>
          </div>
        </div>

        <div class="composer">
          <textarea
            v-model="inputValue"
            class="composer__input"
            rows="1"
            placeholder="输入你的研究方向、需要补充的论据，或者让助手开始生成综述..."
          />

          <div class="composer__actions">
            <span class="composer__hint">Shift + Enter 换行</span>
            <button class="send-button" type="button" :disabled="!canSend" @click="sendMessage">
              发送
            </button>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.landing-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(72, 124, 255, 0.1), transparent 28%),
    linear-gradient(180deg, #eef2f8 0%, #f6f8fc 55%, #fbfcfe 100%);
}

.history-drawer {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 20;
  width: 320px;
  padding: 1rem;
  background: rgba(245, 247, 251, 0.94);
  border-right: 1px solid rgba(31, 41, 55, 0.08);
  backdrop-filter: blur(20px);
  transform: translateX(-100%);
  transition: transform 0.24s ease;
}

.history-drawer.is-open {
  transform: translateX(0);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.drawer-kicker,
.hero-kicker {
  margin: 0 0 0.35rem;
  color: #6b7280;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.drawer-header h2,
.hero-copy h1,
.chat-placeholder__body h3 {
  margin: 0;
  color: #111827;
}

.ghost-button,
.history-toggle,
.prompt-card,
.send-button,
.history-item {
  border: none;
  cursor: pointer;
  font: inherit;
}

.ghost-button,
.history-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #111827;
}

.ghost-button {
  padding: 0.65rem 0.95rem;
}

.history-list {
  display: grid;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

.history-item {
  display: grid;
  gap: 0.35rem;
  width: 100%;
  padding: 1rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
  text-align: left;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.history-item strong {
  color: #111827;
}

.history-item p,
.history-time,
.hero-description,
.chat-placeholder__body p,
.composer__hint {
  margin: 0;
  color: #6b7280;
}

.history-time {
  font-size: 0.82rem;
}

.chat-stage {
  min-height: 100vh;
  padding: 1rem 1.25rem 2rem;
  transition: padding-left 0.24s ease;
}

.chat-stage.with-history {
  padding-left: 340px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  max-width: 1040px;
  margin: 0 auto;
}

.history-toggle {
  padding: 0.8rem 1rem;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.history-toggle__icon {
  position: relative;
  width: 1rem;
  height: 0.75rem;
}

.history-toggle__icon::before,
.history-toggle__icon::after,
.history-toggle__icon {
  display: inline-block;
  border-top: 2px solid #111827;
  border-radius: 999px;
}

.history-toggle__icon::before,
.history-toggle__icon::after {
  content: '';
  position: absolute;
  left: 0;
  width: 100%;
}

.history-toggle__icon::before {
  top: 0.25rem;
}

.history-toggle__icon::after {
  top: 0.5rem;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  color: #111827;
  font-weight: 600;
}

.brand-mark__dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.09);
}

.hero-panel,
.chat-card {
  max-width: 1040px;
  margin: 1.25rem auto 0;
  border: 1px solid rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(24px);
}

.hero-panel {
  padding: 3rem;
  border-radius: 32px;
}

.hero-copy {
  max-width: 700px;
}

.hero-copy h1 {
  font-size: clamp(2rem, 4vw, 3.6rem);
  line-height: 1.08;
}

.hero-description {
  margin-top: 1rem;
  font-size: 1.05rem;
  line-height: 1.75;
}

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.95rem;
  margin-top: 2rem;
}

.prompt-card {
  padding: 1rem 1.1rem;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff, #f5f7fb);
  color: #1f2937;
  text-align: left;
  box-shadow: inset 0 0 0 1px rgba(31, 41, 55, 0.06);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.prompt-card:hover {
  transform: translateY(-1px);
  box-shadow:
    inset 0 0 0 1px rgba(59, 130, 246, 0.22),
    0 12px 24px rgba(15, 23, 42, 0.06);
}

.chat-card {
  padding: 1.2rem;
  border-radius: 28px;
}

.chat-placeholder {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), rgba(244, 247, 252, 0.95));
}

.assistant-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 0.95rem;
  background: linear-gradient(135deg, #2563eb, #5b6cff);
  color: #fff;
  font-weight: 700;
  flex-shrink: 0;
}

.chat-placeholder__body {
  display: grid;
  gap: 0.5rem;
}

.composer {
  margin-top: 1rem;
  padding: 0.9rem;
  border-radius: 24px;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18);
}

.composer__input {
  width: 100%;
  min-height: 92px;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: #111827;
  font: inherit;
  line-height: 1.7;
}

.composer__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-top: 0.75rem;
}

.send-button {
  padding: 0.78rem 1.2rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #5b6cff);
  color: #fff;
  transition:
    transform 0.18s ease,
    opacity 0.18s ease;
}

.send-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.send-button:not(:disabled):hover {
  transform: translateY(-1px);
}

@media (max-width: 920px) {
  .chat-stage.with-history {
    padding-left: 1.25rem;
  }

  .history-drawer {
    width: min(88vw, 320px);
  }

  .prompt-grid {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    padding: 2rem 1.35rem;
  }
}

@media (max-width: 640px) {
  .chat-stage {
    padding: 0.9rem 0.8rem 1.2rem;
  }

  .topbar,
  .composer__actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-copy h1 {
    font-size: 2rem;
  }
}
</style>
