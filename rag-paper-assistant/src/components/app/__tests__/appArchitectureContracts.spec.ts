import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

function projectPath(relativePath: string) {
  return resolve(process.cwd(), relativePath)
}

function readSource(relativePath: string) {
  return readFileSync(projectPath(relativePath), 'utf8')
}

describe('app architecture contracts', () => {
  it('让 App.vue 保持极薄入口，只挂载论文助手页面', () => {
    const source = readSource('src/App.vue')

    expect(source).toContain("import PaperAssistantPage from './components/app/PaperAssistantPage.vue'")
    expect(source).toContain('<PaperAssistantPage />')
    expect(source).not.toContain('fetch(')
    expect(source).not.toContain('defineProps')
  })

  it('移除 Vue starter 和已弃用上传入口', () => {
    const removedPaths = [
      `src/components/${'Hello'}${'World'}.vue`,
      `src/components/${'The'}${'Welcome'}.vue`,
      `src/components/${'Welcome'}${'Item'}.vue`,
      `src/${'rou'}${'ter'}/index.ts`,
      'src/stores/counter.ts',
      'src/views/HomeView.vue',
      'src/views/AboutView.vue',
    ]
    const appSource = readSource('src/components/app/PaperAssistantPage.vue')

    for (const relativePath of removedPaths) {
      expect(existsSync(projectPath(relativePath))).toBe(false)
    }
    expect(appSource).not.toContain(`/api/${'upload'}-${'papers'}`)
    expect(appSource).not.toContain(`${'open'}${'File'}${'Picker'}`)
  })

  it('保留 app 页面、工作区和弹窗区的分层入口', () => {
    const pageSource = readSource('src/components/app/PaperAssistantPage.vue')
    const workspaceSource = readSource('src/components/app/PaperAssistantWorkspace.vue')
    const overlaySource = readSource('src/components/app/PaperAssistantOverlayRoot.vue')

    expect(pageSource).toContain('<PaperAssistantWorkspace :app="app" />')
    expect(pageSource).toContain('<PaperAssistantOverlayRoot :app="app" />')
    expect(workspaceSource).toContain('<HistoryDrawer')
    expect(workspaceSource).toContain('<ChatCardStage')
    expect(overlaySource).toContain('<SessionOverlayHost')
    expect(overlaySource).toContain('<LibraryOverlayHost')
    expect(overlaySource).toContain('<TraceOverlayHost')
  })
})
