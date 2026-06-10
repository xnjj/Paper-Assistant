import { expect, test, type Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:8000'

async function mockModelConfig(page: Page) {
  await page.route(`${API_BASE}/api/model-config**`, async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        global_config: {
          llm_model: 'qwen3-max',
          api_key: 'test-key',
          llm_context_length: 200000,
        },
      }),
    })
  })
}

async function mockLibraries(page: Page) {
  await page.route(`${API_BASE}/api/libraries`, async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        libraries: [
          {
            id: 1,
            name: '默认文献库',
            description: '',
            folder_path: 'D:/papers',
            collection_name: 'library_1',
            document_count: 2,
            embedding_model: 'text-embedding-v3',
            embedding_max_input_tokens: 2048,
            chunk_mode: 'recursive',
            created_at: '2026-01-01T00:00:00.000Z',
            updated_at: '2026-01-02T00:00:00.000Z',
          },
        ],
      }),
    })
  })
}

async function mockNoSessions(page: Page) {
  await page.route(`${API_BASE}/api/sessions`, async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ sessions: [] }),
    })
  })
}

async function mockOneSession(page: Page) {
  await page.route(`${API_BASE}/api/sessions`, async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        sessions: [
          {
            id: 1,
            library_id: 1,
            title: 'DQN 自动驾驶综述',
            user_goal: '总结 DQN 在自动驾驶中的应用',
            is_pinned: false,
            created_at: '2026-01-01T00:00:00.000Z',
            updated_at: '2026-01-02T00:00:00.000Z',
          },
        ],
      }),
    })
  })

  await page.route(`${API_BASE}/api/sessions/1/messages`, async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        session_id: 1,
        messages: [
          {
            id: 1,
            session_id: 1,
            role: 'user',
            content: '请总结 DQN 在自动驾驶中的应用。',
            retrieval_context_json: '',
            created_at: '2026-01-01T00:00:00.000Z',
          },
          {
            id: 2,
            session_id: 1,
            role: 'assistant',
            content: 'DQN 常用于自动驾驶决策、路径规划和控制策略优化。',
            retrieval_context_json: '',
            created_at: '2026-01-01T00:01:00.000Z',
          },
        ],
      }),
    })
  })
}

test('home page keeps the refactored app shell and composer visible', async ({ page }) => {
  await mockModelConfig(page)
  await mockLibraries(page)
  await mockNoSessions(page)

  await page.goto('/')

  await expect(page.getByRole('heading', { name: '从本地文献库出发，构建高效研究工作流。' })).toBeVisible()
  await expect(page.locator('.chat-card--home')).toBeVisible()
  await expect(page.locator('.prompt-card')).toHaveCount(4)
  await expect(page.getByPlaceholder('输入你的研究方向、需要补充的论据，或让助手开始生成文献综述...')).toBeVisible()
})

test('session page keeps the chat layout, bubbles and composer controls visible', async ({ page }) => {
  await mockModelConfig(page)
  await mockLibraries(page)
  await mockOneSession(page)

  await page.goto('/')

  await expect(page.locator('.chat-card--session')).toBeVisible()
  await expect(page.locator('.message-stream')).toBeVisible()
  await expect(page.locator('.message-bubble--user')).toBeVisible()
  await expect(page.locator('.message-bubble--assistant')).toBeVisible()
  await expect(page.locator('.composer')).toBeVisible()
  await expect(page.locator('.sync-button')).toBeVisible()
  await expect(page.locator('.send-button')).toBeVisible()
})
