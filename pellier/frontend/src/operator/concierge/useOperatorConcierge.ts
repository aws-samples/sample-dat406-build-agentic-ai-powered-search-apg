/**
 * One controller for the Concierge pane. Components render; this owns server truth.
 *
 * Scattering `fetchCapabilities()` / `createSession()` / `appendTurn()` across
 * components is how a surface ends up with four opinions about whether a governed
 * action is available. Every server fact enters here.
 *
 * Two deliberate behaviours:
 *
 *   Lazy sessions      Opening a client record must not create a database
 *                      conversation. Thousands of empty threads would be the
 *                      cost of a page view. A session is created when the
 *                      operator first submits.
 *
 *   Concurrent reads   Capability, config, and latest-session are independent, so
 *                      they run together. The client record itself is already a
 *                      ~1s parallel read; turning the right pane into a serial
 *                      waterfall on top of it would undo that.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  createConciergeSession,
  fetchCapabilities,
  fetchConciergeConfig,
  fetchConciergeSession,
  fetchLatestConciergeSession,
  streamConciergeTurn,
} from '../../services/operator'
import type {
  CapabilitySnapshot,
  ConciergeConfig,
  ConciergeInvestigationStep,
  ConciergeMessage,
  ConciergeStreamAnswer,
} from '../../services/operator'

export type ConciergeStatus =
  | 'loading'
  | 'ready'
  | 'read_only'
  | 'submitting'
  | 'capability_unverified'
  | 'conversation_unavailable'

export interface ConciergeController {
  status: ConciergeStatus
  capabilities: CapabilitySnapshot | null
  config: ConciergeConfig | null
  sessionId: string | null
  messages: ConciergeMessage[]
  /** True when a governed write is currently reachable. */
  governedActionsAvailable: boolean
  composerEnabled: boolean
  error: string | null
  /** Real steps arriving during an in-flight turn. Empty when idle. */
  liveSteps: ConciergeInvestigationStep[]
  /** The request currently in flight, so it renders before the answer exists. */
  pendingRequest: string | null
  /** Durable server answer, visible while post-answer work and history reload finish. */
  liveAnswer: ConciergeStreamAnswer | null
  submit: (message: string) => Promise<void>
}

/** A stable key per submission so a network retry cannot duplicate the turn. */
function transportKey(): string {
  const random = globalThis.crypto?.randomUUID?.()
  return random ?? `tk-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function useOperatorConcierge(clientId: string): ConciergeController {
  const [capabilities, setCapabilities] = useState<CapabilitySnapshot | null>(null)
  const [config, setConfig] = useState<ConciergeConfig | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ConciergeMessage[]>([])
  const [status, setStatus] = useState<ConciergeStatus>('loading')
  const [error, setError] = useState<string | null>(null)
  const [liveSteps, setLiveSteps] = useState<ConciergeInvestigationStep[]>([])
  const [pendingRequest, setPendingRequest] = useState<string | null>(null)
  const [liveAnswer, setLiveAnswer] = useState<ConciergeStreamAnswer | null>(null)
  const active = useRef(true)

  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
    }
  }, [])

  useEffect(() => {
    if (!clientId) return
    setStatus('loading')
    setError(null)
    setMessages([])
    setSessionId(null)
    setLiveAnswer(null)

    // Independent reads, so concurrently. `allSettled` because a capability
    // read failing must not hide the conversation, and vice versa.
    void Promise.allSettled([
      fetchCapabilities(),
      fetchConciergeConfig(),
      fetchLatestConciergeSession(clientId),
    ]).then(async ([caps, cfg, latest]) => {
      if (!active.current) return

      if (caps.status === 'fulfilled') {
        setCapabilities(caps.value)
      } else {
        // A control-plane read failure is NOT a governance state. Keep them
        // distinguishable: the backend already fails closed, and if even that
        // could not be reached we say so rather than implying a closed rail.
        setCapabilities(null)
      }
      if (cfg.status === 'fulfilled') setConfig(cfg.value)

      let resumed: string | null = null
      if (latest.status === 'fulfilled') resumed = latest.value

      if (resumed) {
        try {
          const session = await fetchConciergeSession(clientId, resumed)
          if (!active.current) return
          // Never render another client's conversation. The server binds the
          // session, and a stale id that does not match resets to empty.
          if (session.customerId === clientId) {
            setSessionId(session.sessionId)
            setMessages(session.messages)
          }
        } catch {
          if (!active.current) return
          setStatus('conversation_unavailable')
          return
        }
      }

      if (!active.current) return
      if (caps.status !== 'fulfilled') {
        setStatus('capability_unverified')
      } else {
        setStatus(caps.value.governedActionsAvailable ? 'ready' : 'read_only')
      }
    })
  }, [clientId])

  const governedActionsAvailable = Boolean(capabilities?.governedActionsAvailable)
  const composerEnabled = Boolean(config?.composerEnabled)

  const submit = useCallback(
    async (message: string) => {
      const text = message.trim()
      if (!text || !composerEnabled) return
      setStatus('submitting')
      setError(null)
      setLiveSteps([])
      setLiveAnswer(null)
      // Show the request immediately. Seven seconds of stillness after pressing
      // Enter is the single worst part of the experience, and the request is a fact
      // as soon as it is sent.
      setPendingRequest(text)
      try {
        // Lazy creation: the first submission is what makes a thread exist.
        const id = sessionId ?? (await createConciergeSession(clientId)).sessionId
        if (!active.current) return
        setSessionId(id)

        await streamConciergeTurn(
          clientId,
          id,
          text,
          transportKey(),
          (step) => {
            if (!active.current) return
            setLiveSteps((prev) => {
              // A `running` step is replaced by its completed form rather than
              // duplicated, so the list reflects state instead of history.
              const next = prev.filter((s) => s.kind !== step.kind)
              return [...next, step]
            })
          },
          (answer) => {
            if (!active.current) return
            setLiveAnswer(answer)
          },
        )
        if (!active.current) return

        // Reload rather than optimistically appending: the server owns turn state,
        // and a replayed submission must not show twice.
        const session = await fetchConciergeSession(clientId, id)
        if (!active.current) return
        setMessages(session.customerId === clientId ? session.messages : [])
        setPendingRequest(null)
        setLiveSteps([])
        setLiveAnswer(null)
        setStatus(governedActionsAvailable ? 'ready' : 'read_only')
      } catch (err) {
        if (!active.current) return
        setError(err instanceof Error ? err.message : 'operator_unavailable')
        setPendingRequest(null)
        setLiveSteps([])
        setLiveAnswer(null)
        setStatus(governedActionsAvailable ? 'ready' : 'read_only')
      }
    },
    [clientId, composerEnabled, governedActionsAvailable, sessionId],
  )

  return useMemo(
    () => ({
      status,
      capabilities,
      config,
      sessionId,
      messages,
      governedActionsAvailable,
      composerEnabled,
      error,
      liveSteps,
      pendingRequest,
      liveAnswer,
      submit,
    }),
    [
      status,
      capabilities,
      config,
      sessionId,
      messages,
      governedActionsAvailable,
      composerEnabled,
      error,
      liveSteps,
      pendingRequest,
      liveAnswer,
      submit,
    ],
  )
}
