import { readdirSync, readFileSync, statSync } from 'node:fs'
import { relative, resolve, sep } from 'node:path'

import { describe, expect, it } from 'vitest'

const sourceRoot = resolve(process.cwd(), 'src')

function joinToken(parts: string[]) {
  return parts.join('')
}

function collectSourceFiles(directory: string): string[] {
  const files: string[] = []
  for (const entry of readdirSync(directory)) {
    const fullPath = resolve(directory, entry)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      if (entry === '__tests__') {
        continue
      }
      files.push(...collectSourceFiles(fullPath))
      continue
    }
    if (fullPath.endsWith('.vue') || fullPath.endsWith('.ts')) {
      files.push(fullPath)
    }
  }
  return files
}

function readRelativeSource(filePath: string) {
  return {
    relativePath: relative(sourceRoot, filePath).split(sep).join('/'),
    source: readFileSync(filePath, 'utf8'),
  }
}

describe('source hygiene contracts', () => {
  it('不让已弃用入口和上传附件逻辑回流到运行时代码', () => {
    const forbiddenTokens = [
      ['open', 'File', 'Picker'],
      ['handle', 'File', 'Change'],
      ['uploaded', 'Files'],
      ['selected', 'File', 'Names'],
      ['file', 'Input'],
      ['/api/', 'upload', '-', 'papers'],
      ['Hello', 'World'],
      ['The', 'Welcome'],
      ['Welcome', 'Item'],
      ['create', 'Router'],
      ['create', 'Pinia'],
      ['rou', 'ter'],
      ['pin', 'ia'],
    ].map(joinToken)

    const matches = collectSourceFiles(sourceRoot).flatMap((filePath) => {
      const { relativePath, source } = readRelativeSource(filePath)
      return forbiddenTokens
        .filter((token) => source.includes(token))
        .map((token) => `${relativePath}: ${token}`)
    })

    expect(matches).toEqual([])
  })

  it('限制会话样式相关的 deep/global 选择器只出现在布局白名单中', () => {
    const riskyChatStageGlobal = joinToken([':global', '(.chat-stage'])
    const riskyMessageBubbleGlobal = joinToken([':global', '(.message-bubble'])
    const deepSelector = joinToken([':de', 'ep('])
    const matches = collectSourceFiles(sourceRoot).flatMap((filePath) => {
      const { relativePath, source } = readRelativeSource(filePath)
      const hits: string[] = []
      if (source.includes(riskyChatStageGlobal) || source.includes(riskyMessageBubbleGlobal)) {
        hits.push(`${relativePath}: risky global session selector`)
      }
      if (source.includes(deepSelector) && relativePath !== 'components/layout/AppStage.vue') {
        hits.push(`${relativePath}: unexpected deep selector`)
      }
      return hits
    })

    expect(matches).toEqual([])
  })
})
