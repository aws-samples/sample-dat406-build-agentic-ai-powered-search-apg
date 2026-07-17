/**
 * Layout Context — Coordinates chat mode, workshop mode, and main content margin.
 * Persists workshop mode to localStorage.
 */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

type ChatMode = 'floating' | 'docked'
export type WorkshopMode = 'legacy' | 'search' | 'agentic' | 'production'

interface LayoutContextType {
  chatMode: ChatMode
  setChatMode: (mode: ChatMode) => void
  chatOpen: boolean
  setChatOpen: (open: boolean) => void
  mainContentMarginRight: number
  workshopMode: WorkshopMode
  setWorkshopMode: (mode: WorkshopMode) => void
  guardrailsEnabled: boolean
  setGuardrailsEnabled: (enabled: boolean) => void
}

const LayoutContext = createContext<LayoutContextType | undefined>(undefined)

export function useLayout() {
  const ctx = useContext(LayoutContext)
  if (!ctx) throw new Error('useLayout must be used within LayoutProvider')
  return ctx
}

export function LayoutProvider({ children }: { children: ReactNode }) {
  const [chatMode, setChatMode] = useState<ChatMode>('docked')
  const [chatOpen, setChatOpen] = useState(false)
  const [workshopMode, setWorkshopModeRaw] = useState<WorkshopMode>(() => {
    const saved = localStorage.getItem('pellier-workshop-mode')
    if (saved && ['legacy', 'search', 'agentic', 'production'].includes(saved)) return saved as WorkshopMode
    return 'legacy'
  })
  const [guardrailsEnabled, setGuardrailsEnabled] = useState(false)

  const setWorkshopMode = useCallback((mode: WorkshopMode) => {
    setWorkshopModeRaw(mode)
    localStorage.setItem('pellier-workshop-mode', mode)
  }, [])

  const mainContentMarginRight = chatMode === 'docked' && chatOpen ? 420 : 0

  return (
    <LayoutContext.Provider value={{ chatMode, setChatMode, chatOpen, setChatOpen, mainContentMarginRight, workshopMode, setWorkshopMode, guardrailsEnabled, setGuardrailsEnabled }}>
      {children}
    </LayoutContext.Provider>
  )
}
