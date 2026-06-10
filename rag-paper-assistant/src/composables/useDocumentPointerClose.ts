import { onBeforeUnmount, onMounted } from 'vue'

// 监听文档点击：点击会话菜单和弹窗外部时关闭会话菜单，弹窗内部点击不打断操作。
export function useDocumentPointerClose(closeSessionMenu: () => void) {
  function handleDocumentPointerDown(event: PointerEvent) {
    const target = event.target
    if (!(target instanceof HTMLElement)) {
      return
    }
    if (target.closest('[data-session-menu-root]') || target.closest('.dialog-mask')) {
      return
    }
    closeSessionMenu()
  }

  onMounted(() => {
    document.addEventListener('pointerdown', handleDocumentPointerDown)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', handleDocumentPointerDown)
  })
}
