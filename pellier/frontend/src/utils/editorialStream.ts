export interface EditorialStreamController {
  push: (delta: string) => void
  reset: () => void
  settle: () => Promise<void>
  cancel: () => void
}

interface EditorialStreamOptions {
  onAppend: (chunk: string) => void
  onReset: () => void
  cadenceMs?: number
  reducedMotion?: boolean
}

export function splitEditorialDelta(delta: string): string[] {
  return delta.match(/\S+\s*|\s+/g) ?? []
}

function nextDelay(chunk: string, backlog: number, cadenceMs: number): number {
  const tail = chunk.trimEnd()
  const punctuationPause = /[.!?]["')\]]?$/.test(tail)
    ? 1.8
    : /[,;:]["')\]]?$/.test(tail)
      ? 1.35
      : 1
  const catchUp = backlog > 48 ? 0.55 : backlog > 24 ? 0.75 : 1
  return Math.max(12, Math.round(cadenceMs * punctuationPause * catchUp))
}

export function createEditorialStreamController({
  onAppend,
  onReset,
  cadenceMs = 34,
  reducedMotion = false,
}: EditorialStreamOptions): EditorialStreamController {
  let queue: string[] = []
  let timer: ReturnType<typeof setTimeout> | null = null
  let nextAppendAt = 0
  let cancelled = false
  let idleResolvers: Array<() => void> = []

  const resolveIdle = () => {
    if (queue.length > 0 || timer !== null) return
    idleResolvers.forEach(resolve => resolve())
    idleResolvers = []
  }

  const schedule = () => {
    if (cancelled || timer !== null || queue.length === 0) {
      resolveIdle()
      return
    }

    const waitMs = Math.max(0, nextAppendAt - Date.now())
    if (waitMs > 0) {
      timer = setTimeout(drain, waitMs)
      return
    }

    drain()
  }

  const drain = () => {
    timer = null
    if (cancelled || queue.length === 0) {
      resolveIdle()
      return
    }

    const chunk = queue.shift()
    if (chunk) {
      onAppend(chunk)
      nextAppendAt = Date.now() + nextDelay(chunk, queue.length, cadenceMs)
    }
    schedule()
  }

  return {
    push(delta: string) {
      if (cancelled || !delta) return
      if (reducedMotion) {
        onAppend(delta)
        return
      }
      queue.push(...splitEditorialDelta(delta))
      schedule()
    },

    reset() {
      if (timer !== null) clearTimeout(timer)
      timer = null
      queue = []
      nextAppendAt = 0
      onReset()
      resolveIdle()
    },

    settle() {
      if (queue.length === 0 && timer === null) return Promise.resolve()
      return new Promise<void>(resolve => {
        idleResolvers.push(resolve)
      })
    },

    cancel() {
      cancelled = true
      if (timer !== null) clearTimeout(timer)
      timer = null
      queue = []
      resolveIdle()
    },
  }
}
