import { describe, expect, it } from 'vitest'

import { consumeSseStream } from '../sseStream'

import type { StreamEvent } from '../../types/chat'

function buildSseResponse(chunks: string[]) {
  const encoder = new TextEncoder()
  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk))
        }
        controller.close()
      },
    }),
  )
}

describe('consumeSseStream', () => {
  it('consumes SSE events split across multiple response chunks', async () => {
    const events: StreamEvent[] = []
    const response = buildSseResponse([
      'data: {"type":"delta","content":"第一',
      '段"}\n\n',
      'data: {"type":"done","answer":"完成"}',
    ])

    await consumeSseStream(response, (event) => {
      events.push(event)
    })

    expect(events).toEqual([
      { type: 'delta', content: '第一段' },
      { type: 'done', answer: '完成' },
    ])
  })

  it('ignores empty or non-data SSE blocks', async () => {
    const events: StreamEvent[] = []
    const response = buildSseResponse([': keep-alive\n\n', '\n\n', 'data: {"type":"delta","content":"ok"}\n\n'])

    await consumeSseStream(response, (event) => {
      events.push(event)
    })

    expect(events).toEqual([{ type: 'delta', content: 'ok' }])
  })
})
