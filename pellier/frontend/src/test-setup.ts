// Vitest global setup — installs jest-dom matchers and resets between tests.
import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

function createMemoryStorage(): Storage {
  const values = new Map<string, string>()

  return {
    get length() {
      return values.size
    },
    clear() {
      values.clear()
    },
    getItem(key: string) {
      return values.get(String(key)) ?? null
    },
    key(index: number) {
      return Array.from(values.keys())[index] ?? null
    },
    removeItem(key: string) {
      values.delete(String(key))
    },
    setItem(key: string, value: string) {
      values.set(String(key), String(value))
    },
  }
}

// Newer Node releases expose incomplete Web Storage globals unless started
// with --localstorage-file. Install browser-shaped stores before app modules.
const localStorageStub = createMemoryStorage()
const sessionStorageStub = createMemoryStorage()
Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: localStorageStub,
})
Object.defineProperty(globalThis, 'sessionStorage', {
  configurable: true,
  value: sessionStorageStub,
})
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: localStorageStub,
  })
  Object.defineProperty(window, 'sessionStorage', {
    configurable: true,
    value: sessionStorageStub,
  })
}

// ResizeObserver polyfill — jsdom doesn't ship one. react-resizable-panels
// calls ``new ResizeObserver(...)`` from Group's mount effect, which
// throws "n is not a constructor" in tests without this shim. Minimal
// stub: accept the callback, expose no-op observe/unobserve so the
// library's cleanup path is safe.
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
}

// IntersectionObserver polyfill — jsdom doesn't ship one, and Framer Motion's
// ``whileInView`` constructs one from its mount effect, so any component using
// scroll-reveal throws "IntersectionObserver is not defined" without this.
//
// The stub reports the target as intersecting straight away rather than staying
// silent. A silent stub would leave every reveal stuck at its ``initial``
// opacity, so tests would assert against a state no real browser settles on.
if (typeof globalThis.IntersectionObserver === 'undefined') {
  globalThis.IntersectionObserver = class {
    private readonly callback: IntersectionObserverCallback

    constructor(callback: IntersectionObserverCallback) {
      this.callback = callback
    }

    observe(target: Element) {
      this.callback(
        [{ isIntersecting: true, target } as IntersectionObserverEntry],
        this as unknown as IntersectionObserver,
      )
    }

    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [] as IntersectionObserverEntry[]
    }
  } as unknown as typeof IntersectionObserver
}

// scrollIntoView stub — jsdom implements no scrolling at all, so any click
// handler that scrolls (the Labs hero CTA, inspecting a curated turn) throws
// an uncaught TypeError mid-test even though the assertions still pass.
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {}
}

// matchMedia default — jsdom doesn't ship this either. Tests that care
// about responsive behavior override this per-test.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia
}

// jsdom logs a not-implemented stack before returning null. Exercise the
// component's existing no-canvas branch without polluting successful test runs.
Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  configurable: true,
  value: vi.fn(() => null),
})

afterEach(() => {
  cleanup()
  localStorageStub.clear()
  sessionStorageStub.clear()
})
