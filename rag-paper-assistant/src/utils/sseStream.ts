import { parseSseEvent } from './messageMappers'

import type { StreamEvent } from '../types/chat'

// 消费后端 SSE 响应，将底层 reader/buffer 细节封装为逐个 StreamEvent 回调。
export async function consumeSseStream(
  response: Response,
  onEvent: (event: StreamEvent) => Promise<void> | void,
) {
  if (!response.body) {
    throw new Error('流式响应体为空')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      buffer += decoder.decode()
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const eventBlocks = buffer.split('\n\n')
    buffer = eventBlocks.pop() ?? ''

    for (const block of eventBlocks) {
      await applyParsedEvent(block, onEvent)
    }
  }

  await applyParsedEvent(buffer, onEvent)
}

async function applyParsedEvent(rawBlock: string, onEvent: (event: StreamEvent) => Promise<void> | void) {
  const event = parseSseEvent(rawBlock)
  if (!event) {
    return
  }

  await onEvent(event)
}
