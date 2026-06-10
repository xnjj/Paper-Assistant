import { ref } from 'vue'

// 驱动准备区“正在思考 x.xs”的实时刷新，并统一清理定时器。
export function usePreparationTicker() {
  const preparationTicker = ref(Date.now())
  let preparationTimerId: number | null = null

  function startPreparationTimer() {
    preparationTicker.value = Date.now()
    if (preparationTimerId !== null) {
      return
    }
    preparationTimerId = window.setInterval(() => {
      preparationTicker.value = Date.now()
    }, 1000)
  }

  function stopPreparationTimer() {
    if (preparationTimerId === null) {
      return
    }
    window.clearInterval(preparationTimerId)
    preparationTimerId = null
  }

  return {
    preparationTicker,
    startPreparationTimer,
    stopPreparationTimer,
  }
}
