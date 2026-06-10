import { nextTick, ref } from 'vue'

// 管理消息流滚动和引用卡片定位，避免页面组件直接维护 DOM 滚动细节。
export function useMessageStreamNavigation() {
  const messageStreamRef = ref<HTMLElement | null>(null)
  const followMessageStreamToBottom = ref(false)
  const activeReferenceKey = ref<string | null>(null)
  const expandedReferenceKeys = ref<Record<string, boolean>>({})

  let suppressMessageStreamScroll = false

  function setMessageStreamElement(element: HTMLElement | null) {
    messageStreamRef.value = element
  }

  async function scrollMessageStreamToLatestQuestion() {
    await nextTick()
    const container = messageStreamRef.value
    if (!container) {
      return
    }

    const userMessages = container.querySelectorAll<HTMLElement>('[data-message-role="user"]')
    const lastUserMessage = userMessages[userMessages.length - 1]

    if (!lastUserMessage) {
      scrollMessageStreamToBottomNow()
      return
    }

    const topPadding = 12
    runProgrammaticMessageStreamScroll((streamContainer) => {
      streamContainer.scrollTop = Math.max(lastUserMessage.offsetTop - topPadding, 0)
    })
  }

  function runProgrammaticMessageStreamScroll(action: (container: HTMLElement) => void) {
    const container = messageStreamRef.value
    if (!container) {
      return
    }

    suppressMessageStreamScroll = true
    action(container)
    requestAnimationFrame(() => {
      suppressMessageStreamScroll = false
    })
  }

  function scrollMessageStreamToBottomNow() {
    runProgrammaticMessageStreamScroll((container) => {
      container.scrollTop = container.scrollHeight
    })
  }

  async function scrollMessageStreamToBottom() {
    await nextTick()
    scrollMessageStreamToBottomNow()
  }

  function handleMessageStreamScroll() {
    if (suppressMessageStreamScroll) {
      return
    }

    if (followMessageStreamToBottom.value) {
      followMessageStreamToBottom.value = false
    }
  }

  function buildReferenceKey(messageId: number, referenceNumber: number) {
    return `${messageId}-${referenceNumber}`
  }

  async function activateReference(messageId: number, referenceNumber: number) {
    const referenceKey = buildReferenceKey(messageId, referenceNumber)
    activeReferenceKey.value = referenceKey
    await nextTick()

    const referenceCard = document.querySelector<HTMLElement>(`[data-reference-key="${referenceKey}"]`)
    if (!referenceCard) {
      return
    }

    referenceCard.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'nearest',
    })
  }

  function toggleReferenceExpand(messageId: number, referenceNumber: number) {
    const referenceKey = buildReferenceKey(messageId, referenceNumber)
    expandedReferenceKeys.value = {
      ...expandedReferenceKeys.value,
      [referenceKey]: !expandedReferenceKeys.value[referenceKey],
    }
    void activateReference(messageId, referenceNumber)
  }

  return {
    messageStreamRef,
    followMessageStreamToBottom,
    activeReferenceKey,
    expandedReferenceKeys,
    setMessageStreamElement,
    scrollMessageStreamToLatestQuestion,
    scrollMessageStreamToBottomNow,
    scrollMessageStreamToBottom,
    handleMessageStreamScroll,
    activateReference,
    toggleReferenceExpand,
  }
}
