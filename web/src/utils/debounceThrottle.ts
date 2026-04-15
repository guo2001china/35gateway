export type AnyFn = (...args: any[]) => any

// 防抖函数
export function debounceFn<T extends AnyFn>(
  fn: T,
  wait = 300,  
  options?: { 
    leading?: boolean; // 是否立即调用
    trailing?: boolean // 是否在 wait 时间后调用
  }
): ((...args: Parameters<T>) => void) & { cancel: () => void; flush: () => void } {
  let timer: number | null = null
  let lastArgs: Parameters<T> | null = null
  let lastThis: any

  const leading = !!options?.leading
  const trailing = options?.trailing !== false

  const invoke = () => {
    const args = lastArgs as Parameters<T>
    const ctx = lastThis
    lastArgs = null
    lastThis = null
    fn.apply(ctx, args)
  }

  const debounced = function (this: any, ...args: Parameters<T>) {
    lastArgs = args
    lastThis = this
    const shouldCallLeading = leading && !timer

    if (timer) {
      clearTimeout(timer)
    }
    timer = window.setTimeout(() => {
      timer = null
      if (trailing && lastArgs) {
        invoke()
      }
    }, wait)

    if (shouldCallLeading) {
      invoke()
    }
  } as ((...args: Parameters<T>) => void) & { cancel: () => void; flush: () => void }

  debounced.cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    lastArgs = null
    lastThis = null
  }

  debounced.flush = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    if (lastArgs) {
      invoke()
    }
  }

  return debounced
}

export function throttleFn<T extends AnyFn>(
  fn: T,
  wait = 300,
  options?: { leading?: boolean; trailing?: boolean }
): ((...args: Parameters<T>) => void) & { cancel: () => void } {
  let lastCallTime = 0
  let timer: number | null = null
  let lastArgs: Parameters<T> | null = null
  let lastThis: any

  const leading = options?.leading !== false
  const trailing = options?.trailing !== false

  const invoke = () => {
    const args = lastArgs as Parameters<T>
    const ctx = lastThis
    lastArgs = null
    lastThis = null
    fn.apply(ctx, args)
  }

  const throttled = function (this: any, ...args: Parameters<T>) {
    const now = Date.now()
    if (!lastCallTime && !leading) {
      lastCallTime = now
    }

    const remaining = wait - (now - lastCallTime)
    lastArgs = args
    lastThis = this

    if (remaining <= 0 || remaining > wait) {
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      lastCallTime = now
      invoke()
    } else if (trailing && !timer) {
      timer = window.setTimeout(() => {
        timer = null
        if (!leading) {
          lastCallTime = Date.now()
        }
        if (lastArgs) {
          lastCallTime = Date.now()
          invoke()
        }
      }, remaining)
    }
  } as ((...args: Parameters<T>) => void) & { cancel: () => void }

  throttled.cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    lastCallTime = 0
    lastArgs = null
    lastThis = null
  }

  return throttled
}

/**
 * 使用示例
 * --------------------------------------------------
 * 引入：
 *   import { debounceFn, throttleFn } from '@/utils/debounceThrottle'
 *
 * 示例：
 *   // 输入框防抖：300 ms 内无新输入才触发搜索
 *   const onInput = debounceFn((v: string) => search(v), 300)
 *
 *   // 滚动节流：每 200 ms 最多触发一次埋点
 *   const onScroll = throttle(() => track(), 200)
 *
 * 选项：
 *   // 防抖：首次立即执行，后续尾部执行
 *   debounce(fn, 300, { leading: true })
 *
 *   // 节流：只在领先边界触发，尾部不再执行
 *   throttle(fn, 200, { trailing: false })
 */
